import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from PIL import Image
from matrix_processor import UPSMatrixProcessor

class InvoiceParser:
    def __init__(self):
        """Initialize UPS Invoice Matrix Parser with enhanced accuracy"""
        self.matrix_processor = UPSMatrixProcessor()
        
    def is_invoice_page(self, words: List[str]) -> bool:
        """Check if page contains invoice data"""
        text_lower = ' '.join(words).lower()
        indicators = [
            'delivery service invoice', 
            'tracking number', 
            'account number',
            '1z',  # UPS tracking numbers always start with 1Z
            'published charge',
            'incentive credit',
            'billed charge'
        ]
        return any(indicator in text_lower for indicator in indicators)

    def parse_invoice(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
        """
        Parse invoice data using enhanced matrix-based extraction
        Returns list of shipments with all available fields
        """
        if not self.is_invoice_page(words):
            return []
        
        try:
            # Combine words with spatial information for better parsing
            text_with_coords = self._create_spatial_text(words, boxes)
            full_text = ' '.join(words)
            
            print(f"DEBUG: Processing text of length {len(full_text)}")
            print(f"DEBUG: First 500 chars: {full_text[:500]}")
            
            # Extract invoice-level data (common to all shipments)
            invoice_data = self._extract_invoice_level_data(full_text)
            print(f"DEBUG: Invoice data extracted: {invoice_data}")
            
            # Enhanced shipment matrix splitting using coordinate information
            shipment_matrices = self._split_into_enhanced_shipment_matrices(full_text, text_with_coords)
            print(f"DEBUG: Found {len(shipment_matrices)} shipment matrices")
            
            # Process each matrix using the enhanced matrix processor
            result_list = []
            for i, matrix in enumerate(shipment_matrices):
                print(f"DEBUG: Processing matrix {i+1}:")
                print(f"Matrix text preview: {matrix['matrix_text'][:200]}...")
                
                shipment_data = self.matrix_processor.process_shipment_matrix(
                    matrix['matrix_text'], 
                    invoice_data,
                    matrix.get('coordinate_data', {})
                )
                
                if shipment_data and shipment_data.get('tracking_number'):
                    # Add matrix-specific metadata
                    shipment_data['matrix_index'] = i + 1
                    shipment_data['processing_type'] = 'Matrix-Based'
                    result_list.append(shipment_data)
                    print(f"DEBUG: Shipment {i+1} processed successfully: {shipment_data.get('tracking_number')}")
                    print(f"DEBUG: Fields populated: {len([k for k, v in shipment_data.items() if v])}")
                else:
                    print(f"DEBUG: Matrix {i+1} failed to extract valid shipment data")
            
            return result_list
            
        except Exception as e:
            print(f"Error in parsing: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _create_spatial_text(self, words: List[str], boxes: List[List[int]]) -> Dict:
        """Create spatial mapping of text for better matrix parsing"""
        spatial_data = {
            'words': [],
            'lines': [],
            'columns': []
        }
        
        # Create word-coordinate pairs
        word_coords = []
        for i, (word, box) in enumerate(zip(words, boxes)):
            word_coords.append({
                'text': word,
                'x': box[0],
                'y': box[1],
                'width': box[2] - box[0],
                'height': box[3] - box[1],
                'index': i
            })
        
        # Group words by approximate lines (same Y coordinate within tolerance)
        lines = self._group_words_by_lines(word_coords)
        spatial_data['lines'] = lines
        
        # Identify columnar structure
        columns = self._identify_column_structure(lines)
        spatial_data['columns'] = columns
        
        return spatial_data
    
    def _group_words_by_lines(self, word_coords: List[Dict], y_tolerance: int = 5) -> List[List[Dict]]:
        """Group words into lines based on Y coordinates"""
        if not word_coords:
            return []
        
        # Sort by Y coordinate
        sorted_words = sorted(word_coords, key=lambda w: w['y'])
        
        lines = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0]['y']
        
        for word in sorted_words[1:]:
            if abs(word['y'] - current_y) <= y_tolerance:
                current_line.append(word)
            else:
                # Sort current line by X coordinate
                current_line.sort(key=lambda w: w['x'])
                lines.append(current_line)
                current_line = [word]
                current_y = word['y']
        
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w['x'])
            lines.append(current_line)
        
        return lines
    
    def _identify_column_structure(self, lines: List[List[Dict]]) -> Dict:
        """Identify column structure for matrix parsing"""
        if not lines:
            return {}
        
        # Find common X positions across lines
        x_positions = {}
        for line in lines:
            for word in line:
                x = word['x']
                # Group X positions within tolerance
                matched = False
                for existing_x in x_positions:
                    if abs(x - existing_x) <= 20:  # 20px tolerance
                        x_positions[existing_x].append(word)
                        matched = True
                        break
                if not matched:
                    x_positions[x] = [word]
        
        # Sort columns by X position
        sorted_columns = sorted(x_positions.items())
        
        return {
            'column_positions': [x for x, words in sorted_columns],
            'column_data': dict(sorted_columns)
        }
    
    def _extract_invoice_level_data(self, text: str) -> Dict[str, str]:
        """FIXED: Extract data that's common to all shipments in the invoice with enhanced patterns"""
        invoice_data = {}
        
        # Enhanced Invoice Number patterns
        invoice_patterns = [
            r'Invoice\s+Number\s+([A-Z0-9]{10,})',
            r'Invoice\s+Date.*?Invoice\s+Number\s+([A-Z0-9]{10,})',
            r'([0-9A-Z]{10,})\s*(?=.*Account\s+Number)',
            r'Invoice\s+Number\s*:\s*([A-Z0-9]{10,})',
            r'Delivery\s+Service\s+Invoice.*?([0-9A-Z]{10,})'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                invoice_data['invoice_number'] = match.group(1).strip()
                break
        
        # Enhanced Account Number patterns
        account_patterns = [
            r'Account\s+Number\s+([A-Z0-9]{4,})',
            r'Account\s+Number\s*:\s*([A-Z0-9]{4,})',
            r'Account\s+([A-Z0-9]{4,})(?=\s)',
            r'AccountNumber\s*([A-Z0-9]{4,})'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['account_number'] = match.group(1).strip()
                break
        
        # Enhanced Invoice Date patterns
        date_patterns = [
            r'Invoice\s+Date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            r'Invoice\s+Date\s*:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            r'Invoice\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['invoice_date'] = match.group(1).strip()
                try:
                    # Try to extract year for date processing
                    year_match = re.search(r'\d{4}', match.group(1))
                    if year_match:
                        invoice_data['invoice_year'] = int(year_match.group())
                except:
                    invoice_data['invoice_year'] = datetime.now().year
                break
        
        # Control ID
        control_patterns = [
            r'Control\s+ID\s+([A-Z0-9\-#]+)',
            r'Control\s*ID\s*:\s*([A-Z0-9\-#]+)'
        ]
        
        for pattern in control_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['control_id'] = match.group(1).strip()
                break
        
        # FIXED: Extract sender information from invoice header ONLY
        # Look for company-level sender info, not shipment-level receiver info
        sender_patterns = [
            # Look for company name in invoice header section
            r'(?:Ship\s+From|Shipped\s+from):\s*([A-Z][A-Za-z0-9\s&\.,\(\)\-\']+?)(?:\s+\d|\n)',
            r'From:\s*([A-Z][A-Za-z0-9\s&\.,\(\)\-\']+?)(?:\s+\d|\n)',
            # Look for business names near the top of invoice
            r'([A-Z][A-Z\s&\.,\(\)\-\']{2,40})\s*\([A-Z\-]+\)',  # Company (CODE) format
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                sender_name = self._clean_company_name(match.group(1))
                if self._is_valid_company_name(sender_name):
                    invoice_data['sender_name'] = sender_name
                    break
        
        # FIXED: Extract sender address from invoice header
        sender_address_patterns = [
            # Look for address after company name/code
            r'([A-Z][A-Za-z0-9\s&\.,\(\)\-\']+?)\s*\([A-Z\-]+\)\s*,?\s*(\d+[^\n]+)',
            r'(?:Ship\s+From|From):\s*[^,\n]+,\s*([0-9][^\n]+)',
        ]
        
        for pattern in sender_address_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                if len(match.groups()) >= 2:
                    sender_address = self._clean_address(match.group(2))
                else:
                    sender_address = self._clean_address(match.group(1))
                    
                if self._is_valid_address(sender_address):
                    invoice_data['sender_address'] = sender_address
                    break
        
        return invoice_data
    
    def _split_into_enhanced_shipment_matrices(self, text: str, spatial_data: Dict) -> List[Dict]:
        """Enhanced shipment matrix splitting using both text and coordinate data"""
        matrices = []
        
        # Primary pattern: tracking numbers with dates
        tracking_pattern = r'(\d{2}/\d{2}(?:/\d{2,4})?)\s+(1Z[A-Z0-9]{16})'
        boundaries = list(re.finditer(tracking_pattern, text))
        
        print(f"DEBUG: Found {len(boundaries)} primary shipment boundaries")
        
        # If no primary boundaries found, try alternative patterns
        if not boundaries:
            alt_patterns = [
                r'(1Z[A-Z0-9]{16})',  # Just tracking numbers
                r'(\d{2}/\d{2})\s+.*?(Ground|Air|Express)',  # Date + service
                r'(Tracking\s+Number:?\s*1Z[A-Z0-9]{16})'
            ]
            
            for alt_pattern in alt_patterns:
                boundaries = list(re.finditer(alt_pattern, text, re.IGNORECASE))
                if boundaries:
                    print(f"DEBUG: Found {len(boundaries)} boundaries using alternative pattern")
                    break
        
        for i, boundary in enumerate(boundaries):
            # Define matrix boundaries
            start_pos = boundary.start()
            
            # Find end position
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1].start()
            else:
                # Look for natural end markers with enhanced patterns
                end_markers = [
                    r'Total\s+for\s+Internet[-\s]*ID',
                    r'Total\s+Shipping\s+API',
                    r'Message\s+Codes:',
                    r'Page\s+\d+\s+of\s+\d+',
                    r'=== (?:INVOICE|END)',
                    r'Consolidated\s+(?:Billing|Remittance)',
                    r'Invoice\s+Messaging',
                    r'Code\s+Message',
                    r'\d{2}/\d{2}\s+1Z[A-Z0-9]{16}'  # Next shipment
                ]
                
                end_pos = len(text)
                for marker in end_markers:
                    marker_match = re.search(marker, text[start_pos:], re.IGNORECASE)
                    if marker_match:
                        potential_end = start_pos + marker_match.start()
                        if potential_end > start_pos + 50:  # Minimum matrix size
                            end_pos = potential_end
                            break
            
            matrix_text = text[start_pos:end_pos].strip()
            
            # Skip if matrix is too small
            if len(matrix_text) < 50:
                continue
            
            # Extract coordinate data for this matrix if available
            coordinate_data = self._extract_matrix_coordinates(spatial_data, start_pos, end_pos)
            
            # Extract basic tracking info
            tracking_match = re.search(r'1Z[A-Z0-9]{16}', matrix_text)
            date_match = re.search(r'\d{2}/\d{2}(?:/\d{2,4})?', matrix_text)
            
            matrix_info = {
                'matrix_text': matrix_text,
                'shipment_date': date_match.group() if date_match else None,
                'tracking_number': tracking_match.group() if tracking_match else None,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'coordinate_data': coordinate_data,
                'matrix_length': len(matrix_text)
            }
            
            matrices.append(matrix_info)
            
            print(f"DEBUG: Matrix {i+1} created:")
            print(f"  - Date: {matrix_info['shipment_date']}")
            print(f"  - Tracking: {matrix_info['tracking_number']}")
            print(f"  - Length: {matrix_info['matrix_length']}")
        
        return matrices
    
    def _extract_matrix_coordinates(self, spatial_data: Dict, start_pos: int, end_pos: int) -> Dict:
        """Extract coordinate information for a specific matrix section"""
        # This would require mapping text positions to coordinate data
        # For now, return empty dict - can be enhanced later
        return {}
    
    def _is_valid_company_name(self, name: str) -> bool:
        """FIXED: Validate if extracted text is a valid company name"""
        if not name or len(name) < 2:
            return False
        
        # Invalid if contains common non-company terms
        invalid_terms = [
            'total', 'charge', 'published', 'incentive', 'billed', 'surcharge',
            'weight', 'dimensions', 'customer', 'fuel', 'residential',
            'message', 'codes', 'adjustment', 'billing', 'correction',
            'internet-id', 'shipping', 'api', 'outbound', 'invoice', 'number',
            'date', 'account', 'ground', 'air', 'express', 'next', 'day',
            'tracking', 'zone', 'pickup', 'delivery'
        ]
        
        name_lower = name.lower()
        for term in invalid_terms:
            if term in name_lower:
                return False
        
        # Valid if contains typical company name patterns
        return bool(re.match(r'^[A-Z][A-Za-z0-9\s&\.,\(\)\-\']+$', name))
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate if extracted text is a valid person name"""
        if not name or len(name) < 2:
            return False
        
        # Invalid if contains common non-name terms
        invalid_terms = [
            'total', 'charge', 'published', 'incentive', 'billed', 'surcharge',
            'weight', 'dimensions', 'customer', 'fuel', 'residential',
            'message', 'codes', 'adjustment', 'billing', 'correction',
            'internet-id', 'shipping', 'api', 'outbound', 'invoice', 'number',
            'date', 'account', 'ground', 'air', 'express', 'tracking'
        ]
        
        name_lower = name.lower()
        for term in invalid_terms:
            if term in name_lower:
                return False
        
        # Valid if contains typical name patterns (person names)
        return bool(re.match(r'^[A-Z][A-Za-z\s\.\-\']+$', name))
    
    def _is_valid_address(self, address: str) -> bool:
        """Validate if extracted text is a valid address"""
        if not address or len(address) < 5:
            return False
        
        # Should start with a number and contain address keywords
        address_indicators = ['street', 'st', 'avenue', 'ave', 'drive', 'dr', 'road', 'rd', 'court', 'ct', 'boulevard', 'blvd', 'lane', 'ln']
        
        return (address[0].isdigit() and 
                any(indicator in address.lower() for indicator in address_indicators))
    
    def _clean_company_name(self, name: str) -> str:
        """FIXED: Clean and validate company name field"""
        if not name:
            return ''
        
        # Remove common non-company words
        exclusions = [
            'Customer', 'Weight', 'Residential', 'Surcharge', 'Fuel', 
            'Next', 'Day', 'Air', 'Ground', 'Total', 'Published', 'Incentive',
            'Charge', 'Credit', 'Billed', 'Dimensions', 'Message', 'Codes',
            'Internet-ID', 'Shipping', 'API', 'Outbound', 'Adjustment',
            'Billing', 'Correction', 'Goodwill', 'Invoice', 'Number', 'Date',
            'Account', 'Tracking', 'Zone', 'Pickup', 'Delivery'
        ]
        
        cleaned = name
        for exclusion in exclusions:
            cleaned = re.sub(rf'\b{exclusion}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove monetary values and numbers that aren't part of names
        cleaned = re.sub(r'\$?[\d,]+\.\d{2}', '', cleaned)
        cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:lb|lbs)\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' .,:-')
        
        return cleaned
    
    def _clean_name(self, name: str) -> str:
        """Clean and validate name field with enhanced cleaning"""
        if not name:
            return ''
        
        # Remove common non-name words more aggressively
        exclusions = [
            'Customer', 'Weight', 'Residential', 'Surcharge', 'Fuel', 
            'Next', 'Day', 'Air', 'Ground', 'Total', 'Published', 'Incentive',
            'Charge', 'Credit', 'Billed', 'Dimensions', 'Message', 'Codes',
            'Internet-ID', 'Shipping', 'API', 'Outbound', 'Adjustment',
            'Billing', 'Correction', 'Goodwill', 'Invoice', 'Number', 'Date',
            'Account'
        ]
        
        cleaned = name
        for exclusion in exclusions:
            cleaned = re.sub(rf'\b{exclusion}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove monetary values and numbers that aren't part of names
        cleaned = re.sub(r'\$?[\d,]+\.\d{2}', '', cleaned)
        cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:lb|lbs)\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' .,:-')
        
        return cleaned
    
    def _clean_address(self, address: str) -> str:
        """Clean and validate address field"""
        if not address:
            return ''
        
        # Remove monetary values and invoice-specific terms
        cleaned = re.sub(r'\$?[\d,]+\.\d{2}(?:\s*-?[\d,]+\.\d{2})*', '', address)
        cleaned = re.sub(r'Total|Published|Incentive|Billed|Customer|Weight|Dimensions', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace
        cleaned = ' '.join(cleaned.split()).strip()
        
        return cleaned
    
    def _parse_currency(self, value: str) -> Optional[float]:
        """Parse currency string to float"""
        if not value:
            return None
        try:
            return float(value.replace(',', '').replace('$', '').strip())
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float value"""
        if not value:
            return None
        try:
            return float(value.replace(',', '').strip())
        except (ValueError, TypeError):
            return None
    
    def _parse_integer(self, value: str) -> Optional[int]:
        """Parse integer value"""
        if not value:
            return None
        try:
            return int(value.replace(',', '').strip())
        except (ValueError, TypeError):
            return None
    
    def _parse_date(self, value: str, invoice_year: int = None) -> Optional[str]:
        """Parse date value and return in ISO format"""
        if not value:
            return None
        try:
            # Handle MM/DD format
            if re.match(r'\d{1,2}/\d{1,2}$', value):
                month, day = value.split('/')
                year = invoice_year or datetime.now().year
                return f"{year}-{int(month):02d}-{int(day):02d}"
            # Handle MM/DD/YYYY format
            elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}$', value):
                month, day, year = value.split('/')
                if len(year) == 2:
                    year = 2000 + int(year)
                return f"{int(year)}-{int(month):02d}-{int(day):02d}"
            # Handle full date formats
            else:
                return value.strip()
        except (ValueError, IndexError):
            return value.strip()
 