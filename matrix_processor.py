"""
FIXED UPS Invoice Matrix Processing Engine
Corrects sender/receiver extraction and totals calculation
"""

import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from ups_field_definitions import UPSFieldMatrix
import logging

logger = logging.getLogger(__name__)

class UPSMatrixProcessor:
    """FIXED processor for UPS invoice matrix extraction with corrected address and totals logic"""
    
    def __init__(self):
        self.field_matrix = UPSFieldMatrix()
        self.compiled_patterns = self.field_matrix.compiled_patterns
        
    def process_shipment_matrix(self, matrix_text: str, invoice_data: Dict[str, Any], coordinate_data: Dict = None) -> Dict[str, Any]:
        """
        FIXED: Process a single shipment matrix with corrected address extraction
        """
        # Initialize shipment with invoice-level data
        shipment = invoice_data.copy()
        
        # Initialize all possible fields with None
        for field_name in self.field_matrix.field_definitions.keys():
            if field_name not in shipment:
                shipment[field_name] = None
        
        print(f"DEBUG: Processing matrix with text length: {len(matrix_text)}")
        print(f"Matrix preview: {matrix_text[:300]}...")
        
        # Step 1: Extract main shipment line (most critical)
        main_line_data = self._extract_main_shipment_line_enhanced(matrix_text)
        if main_line_data:
            shipment.update(main_line_data)
            print(f"DEBUG: Main line extracted: {main_line_data}")
        
        # Step 2: Extract surcharges with three-value patterns
        surcharge_data = self._extract_all_surcharges(matrix_text)
        if surcharge_data:
            shipment.update(surcharge_data)
            print(f"DEBUG: Surcharges extracted: {len(surcharge_data)} items")
        
        # Step 3: Extract reference numbers and IDs
        reference_data = self._extract_references_enhanced(matrix_text)
        if reference_data:
            shipment.update(reference_data)
            print(f"DEBUG: References extracted: {reference_data}")
        
        # Step 4: FIXED - Extract receiver information correctly (not sender)
        receiver_data = self._extract_receiver_information_fixed(matrix_text)
        if receiver_data:
            shipment.update(receiver_data)
            print(f"DEBUG: Receiver data extracted: {receiver_data}")
        
        # Step 5: Extract additional fields using compiled patterns
        for field_name, patterns in self.compiled_patterns.items():
            if field_name in shipment and shipment[field_name] is not None:
                continue  # Skip if already extracted
                
            field_def = self.field_matrix.field_definitions[field_name]
            
            for pattern in patterns:
                match = pattern.search(matrix_text)
                if match:
                    try:
                        self._extract_field_value(shipment, field_name, field_def, match)
                        break  # Stop at first successful match
                    except Exception as e:
                        logger.warning(f"Error extracting {field_name}: {e}")
                        continue
        
        # Step 6: Post-processing and validation
        self._post_process_shipment_data(shipment)
        
        # Step 7: FIXED - Calculate line totals correctly
        self._calculate_correct_totals(shipment)
        
        return shipment
    
    def _extract_receiver_information_fixed(self, matrix_text: str) -> Dict[str, Any]:
        """FIXED: Extract receiver information from shipment matrix (not sender info from invoice header)"""
        
        receiver_data = {}
        
        # Clean matrix text to focus on shipment-specific data
        clean_text = self._isolate_shipment_receiver_section(matrix_text)
        
        print(f"DEBUG: Cleaned receiver section: {clean_text[:200]}...")
        
        # FIXED: Look for receiver name patterns within shipment data
        receiver_name_patterns = [
            # Pattern 1: After "Receiver:" label
            r'Receiver\s*:\s*([A-Z][A-Z\s\.\-\']+?)(?=\s+\d|\n|Message|$)',
            
            # Pattern 2: After tracking number and service in shipment line
            r'1Z[A-Z0-9]{16}.*?(?:Ground|Air|Express|Day).*?(?:Residential|Commercial).*?([A-Z][A-Z\s\.\-\']+?)(?=\s+\d|\n)',
            
            # Pattern 3: Name before address in shipment section
            r'([A-Z][A-Z\s\.\-\']{3,30})(?=\s+\d+\s+[A-Z\s]+(?:STREET|ST|AVENUE|AVE|DRIVE|DR|ROAD|RD|COURT|CT|BOULEVARD|BLVD|LANE|LN))',
            
            # Pattern 4: After zone/weight info, before address
            r'(?:Ground|Air|Express).*?\d{5}\s+\d+\s+[\d\.]+.*?([A-Z][A-Z\s\.\-\']+?)(?=\s+\d+\s)',
            
            # Pattern 5: Specific pattern for names in shipment data
            r'(\b[A-Z][A-Z\s\.\-\']{2,25})\s+(?=\d+\s+[A-Z\s]+(?:STREET|ST|AVENUE|AVE))'
        ]
        
        for pattern in receiver_name_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
            if match:
                receiver_name = self._clean_person_name(match.group(1))
                if self._is_valid_person_name(receiver_name):
                    receiver_data['receiver_name'] = receiver_name
                    print(f"DEBUG: Found receiver name: {receiver_name}")
                    break
        
        # FIXED: Extract receiver address - look for address patterns after receiver name
        if receiver_data.get('receiver_name'):
            receiver_name = receiver_data['receiver_name']
            # Look for address after the receiver name
            address_patterns = [
                # Pattern 1: Address immediately after receiver name
                rf'{re.escape(receiver_name)}\s+(\d+[^\n]+)',
                
                # Pattern 2: Address on next line after receiver name
                rf'{re.escape(receiver_name)}\s*\n\s*(\d+[^\n]+)',
                
                # Pattern 3: Address in same context as receiver name
                rf'([0-9][^,\n]+,\s*[A-Z\s]+,\s*[A-Z]{{2}}\s+\d{{5}}(?:-\d{{4}})?)',
                
                # Pattern 4: Standard address format
                r'(\d+\s+[A-Z\s]+(?:STREET|ST|AVENUE|AVE|DRIVE|DR|ROAD|RD|COURT|CT|BOULEVARD|BLVD|LANE|LN)[^,\n]*,\s*[A-Z\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)'
            ]
            
            for pattern in address_patterns:
                match = re.search(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    address = self._clean_address(match.group(1))
                    if self._is_valid_address(address):
                        receiver_data['receiver_address'] = address
                        print(f"DEBUG: Found receiver address: {address}")
                        break
        
        return receiver_data
    
    def _isolate_shipment_receiver_section(self, text: str) -> str:
        """FIXED: Isolate the shipment-specific receiver section, removing invoice totals contamination"""
        
        # Remove invoice summary sections that contaminate shipment data
        contamination_patterns = [
            r'Total\s+for\s+Internet-ID:.*?(?=\n\s*\n|\Z)',
            r'Total\s+Shipping\s+API.*?(?=\n\s*\n|\Z)',
            r'Total\s+Outbound.*?(?=\n\s*\n|\Z)',
            r'Adjustments\s*&\s*Other\s+Charges.*?(?=\n\s*\n|\Z)',
            r'BILLING\s+ADJUSTMENT.*?(?=\n\s*\n|\Z)',
            r'ADDRESS\s+CORRECTION-GOODWILL.*?(?=\n\s*\n|\Z)',
            r'Total\s+Adjustments.*?(?=\n\s*\n|\Z)',
            r'Invoice\s+Messaging.*?(?=\n\s*\n|\Z)',
            r'Code\s+Message.*?(?=\n\s*\n|\Z)',
            r'Custom\s+Dimensional\s+Weight\s+Applie.*?(?=\n\s*\n|\Z)',
            # Remove sender information from invoice header
            r'(?:Ship\s+From|Shipped\s+from|From):\s*[^\n]+',
            r'Control\s+ID\s+[^\n]+',
            r'Account\s+Number\s+[^\n]+',
            r'Invoice\s+(?:Number|Date)\s+[^\n]+'
        ]
        
        clean_text = text
        for pattern in contamination_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        return clean_text
    
    def _is_valid_person_name(self, name: str) -> bool:
        """FIXED: Validate if extracted text is a valid person name (not company or invoice terms)"""
        if not name or len(name) < 2:
            return False
        
        # Invalid if contains invoice/shipping terms
        invalid_terms = [
            'total', 'charge', 'published', 'incentive', 'billed', 'surcharge',
            'weight', 'dimensions', 'customer', 'fuel', 'residential', 'commercial',
            'message', 'codes', 'adjustment', 'billing', 'correction',
            'internet-id', 'shipping', 'api', 'outbound', 'ground', 'air', 'express',
            'next', 'day', 'service', 'delivery', 'pickup', 'zone', 'tracking',
            'invoice', 'number', 'date', 'account'
        ]
        
        name_lower = name.lower()
        for term in invalid_terms:
            if term in name_lower:
                return False
        
        # Invalid if it looks like a company name pattern
        company_indicators = ['inc', 'corp', 'llc', 'ltd', 'company', 'co.', 'resort', 'hotel', 'center']
        for indicator in company_indicators:
            if indicator in name_lower:
                return False
        
        # Valid if contains typical person name patterns
        return bool(re.match(r'^[A-Z][A-Za-z\s\.\-\']+', name)) and len(name.split()) <= 4
    
    def _clean_person_name(self, name: str) -> str:
        """FIXED: Clean person name (different from company name cleaning)"""
        if not name:
            return ''
        
        # Remove invoice-specific contamination
        exclusions = [
            'Customer', 'Weight', 'Residential', 'Commercial', 'Surcharge', 'Fuel', 
            'Next', 'Day', 'Air', 'Ground', 'Total', 'Published', 'Incentive',
            'Charge', 'Credit', 'Billed', 'Dimensions', 'Message', 'Codes',
            'Internet-ID', 'Shipping', 'API', 'Outbound', 'Adjustment',
            'Billing', 'Correction', 'Goodwill', 'Invoice', 'Number', 'Date',
            'Account', 'Service', 'Delivery', 'Zone', 'Tracking'
        ]
        
        cleaned = name
        for exclusion in exclusions:
            cleaned = re.sub(rf'\b{exclusion}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove monetary values and measurements
        cleaned = re.sub(r'\$?[\d,]+\.\d{2}', '', cleaned)
        cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:lb|lbs|oz)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b\d+\s*x\s*\d+\s*x\s*\d+\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' .,:-')
        
        return cleaned
    
    def _calculate_correct_totals(self, shipment: Dict):
        """FIXED: Calculate line totals correctly based on base charges + surcharges"""
        
        # Calculate line totals as sum of all charges (base + surcharges)
        published_total = 0
        incentive_total = 0
        billed_total = 0
        
        # Add base charges
        if shipment.get('published_charge'):
            published_total += shipment['published_charge']
        if shipment.get('incentive_credit'):
            incentive_total += shipment['incentive_credit']
        if shipment.get('billed_charge'):
            billed_total += shipment['billed_charge']
        
        # Add all surcharges
        surcharge_fields = [
            'fuel_surcharge', 'residential_surcharge', 'delivery_area_surcharge',
            'large_package_surcharge', 'additional_handling', 'saturday_delivery',
            'signature_required', 'adult_signature_required', 'address_correction',
            'over_maximum_limits', 'peak_surcharge', 'hazmat_surcharge',
            'dry_ice_surcharge', 'cod_surcharge'
        ]
        
        for surcharge in surcharge_fields:
            pub_key = f"{surcharge}_published"
            inc_key = f"{surcharge}_incentive"
            bill_key = f"{surcharge}_billed"
            
            if shipment.get(pub_key) and isinstance(shipment[pub_key], (int, float)):
                published_total += shipment[pub_key]
            if shipment.get(inc_key) and isinstance(shipment[inc_key], (int, float)):
                incentive_total += shipment[inc_key]
            if shipment.get(bill_key) and isinstance(shipment[bill_key], (int, float)):
                billed_total += shipment[bill_key]
        
        # Set calculated totals
        if published_total > 0 or incentive_total != 0 or billed_total > 0:
            shipment['line_total_published'] = published_total
            shipment['line_total_incentive'] = incentive_total
            shipment['line_total_billed'] = billed_total
            
            # Also create the triple format
            shipment['line_total'] = {
                'published': published_total,
                'incentive': incentive_total,
                'billed': billed_total
            }
            
            print(f"DEBUG: Calculated totals - Published: {published_total}, Incentive: {incentive_total}, Billed: {billed_total}")
    
    def _extract_main_shipment_line_enhanced(self, matrix_text: str) -> Dict[str, Any]:
        """Enhanced extraction of the main shipment line with multiple pattern attempts"""
        
        main_data = {}
        
        # Enhanced main line patterns based on the sample data
        patterns = [
            # Pattern 1: Full format with all fields
            r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})\s+([A-Za-z\s]+?)\s+(\d{5})\s+(\d{1,4})\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
            
            # Pattern 2: Service type may contain "Residential"
            r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})\s+((?:Ground|Air|Express|Next\s+Day|2nd\s+Day|3\s*Day).*?Residential)\s+(\d{5})\s+(\d{1,4})\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
            
            # Pattern 3: Without explicit zone
            r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})\s+((?:Ground|Air|Express|Next\s+Day|2nd\s+Day|3\s*Day).*?)\s+(\d{5})\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
            
            # Pattern 4: Flexible service name matching
            r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})\s+([^0-9]+?)\s+(\d{5})\s+(\d{1,4})\s+(\d+)\s+([\d,]+\.\d{2})\s*(-[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, matrix_text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    print(f"DEBUG: Main line pattern {i+1} matched with {len(groups)} groups")
                    
                    if len(groups) >= 9:  # Full pattern match
                        main_data.update({
                            'shipment_date': self._parse_date(groups[0]),
                            'pickup_date': self._parse_date(groups[0]),  # Same as shipment date initially
                            'tracking_number': groups[1],
                            'service_type': self._clean_service_name(groups[2]),
                            'destination_zip': groups[3],
                            'zone': self._parse_integer(groups[4]),
                            'weight': self._parse_float(groups[5]),
                            'published_charge': self._parse_currency(groups[6]),
                            'incentive_credit': self._parse_currency(groups[7]),
                            'billed_charge': self._parse_currency(groups[8])
                        })
                    elif len(groups) >= 8:  # Pattern without zone
                        main_data.update({
                            'shipment_date': self._parse_date(groups[0]),
                            'pickup_date': self._parse_date(groups[0]),
                            'tracking_number': groups[1],
                            'service_type': self._clean_service_name(groups[2]),
                            'destination_zip': groups[3],
                            'weight': self._parse_float(groups[4]),
                            'published_charge': self._parse_currency(groups[5]),
                            'incentive_credit': self._parse_currency(groups[6]),
                            'billed_charge': self._parse_currency(groups[7])
                        })
                    
                    print(f"DEBUG: Successfully extracted main line data: {main_data}")
                    return main_data
                    
                except Exception as e:
                    print(f"DEBUG: Error processing pattern {i+1}: {e}")
                    continue
        
        print("DEBUG: No main line pattern matched")
        return main_data
    
    def _extract_all_surcharges(self, matrix_text: str) -> Dict[str, Any]:
        """Extract all surcharges with their published/incentive/billed values"""
        
        surcharge_data = {}
        
        # Define surcharge patterns with three values (published, incentive, billed)
        surcharge_patterns = {
            'residential_surcharge': [
                r'Residential\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'Residential\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'fuel_surcharge': [
                r'Fuel\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'delivery_area_surcharge': [
                r'Delivery\s+Area\s+Surcharge\s*(?:-\s*(?:Extended|Remote))?\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'(?:Extended|Remote)\s+Area\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                r'DAS\s*-\s*(?:Extended|Remote)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'large_package_surcharge': [
                r'Large\s+Package\s+Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'additional_handling': [
                r'Additional\s+Handling\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'saturday_delivery': [
                r'Saturday\s+Delivery\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'signature_required': [
                r'Signature\s+(?:Required|Option)\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'adult_signature_required': [
                r'Adult\s+Signature\s+Required\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'address_correction': [
                r'Address\s+Correction\s*(?:Fee|Charge)?\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'over_maximum_limits': [
                r'Over\s+Maximum\s+Limits\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ],
            'peak_surcharge': [
                r'Peak\s+(?:Season\s+)?Surcharge\s+([\d,]+\.\d{2})\s*(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            ]
        }
        
        for surcharge_name, patterns in surcharge_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, matrix_text, re.IGNORECASE)
                if match:
                    try:
                        published = self._parse_currency(match.group(1))
                        incentive = self._parse_currency(match.group(2))
                        billed = self._parse_currency(match.group(3))
                        
                        surcharge_data[f"{surcharge_name}_published"] = published
                        surcharge_data[f"{surcharge_name}_incentive"] = incentive
                        surcharge_data[f"{surcharge_name}_billed"] = billed
                        
                        # Also store as a dictionary for convenience
                        surcharge_data[surcharge_name] = {
                            'published': published,
                            'incentive': incentive,
                            'billed': billed
                        }
                        
                        print(f"DEBUG: Extracted {surcharge_name}: P={published}, I={incentive}, B={billed}")
                        break  # Stop at first match for this surcharge type
                        
                    except Exception as e:
                        print(f"DEBUG: Error extracting {surcharge_name}: {e}")
                        continue
        
        return surcharge_data
    
    def _extract_references_enhanced(self, matrix_text: str) -> Dict[str, Any]:
        """Enhanced extraction of reference numbers and IDs"""
        
        reference_data = {}
        
        # Enhanced patterns for references
        reference_patterns = {
            'first_reference': [
                r'1st\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*1:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*1:?\s*([A-Za-z0-9\-_]+)'
            ],
            'second_reference': [
                r'2nd\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*2:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*2:?\s*([A-Za-z0-9\-_]+)'
            ],
            'third_reference': [
                r'3rd\s+ref:?\s*([A-Za-z0-9\-_]+)',
                r'Ref\s*3:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*3:?\s*([A-Za-z0-9\-_]+)'
            ],
            'user_id': [
                r'UserID:?\s*([A-Za-z0-9\-_]+)',
                r'User\s*ID:?\s*([A-Za-z0-9\-_]+)',
                r'UID:?\s*([A-Za-z0-9\-_]+)'
            ],
            'purchase_order': [
                r'(?:Purchase\s+Order|PO|P\.O\.)\s*:?\s*([A-Za-z0-9\-_]+)'
            ]
        }
        
        for ref_name, patterns in reference_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, matrix_text, re.IGNORECASE)
                if match:
                    reference_data[ref_name] = match.group(1).strip()
                    print(f"DEBUG: Extracted {ref_name}: {match.group(1)}")
                    break
        
        return reference_data
    
    def _extract_field_value(self, shipment: Dict, field_name: str, field_def, match):
        """Extract field value based on its type with enhanced accuracy"""
        
        try:
            if field_def.data_type == 'currency_triple':
                # Handle surcharge patterns with three values
                if len(match.groups()) >= 3:
                    published = self._parse_currency(match.group(1))
                    incentive = self._parse_currency(match.group(2))
                    billed = self._parse_currency(match.group(3))
                    
                    shipment[f"{field_name}_published"] = published
                    shipment[f"{field_name}_incentive"] = incentive
                    shipment[f"{field_name}_billed"] = billed
                    
                    shipment[field_name] = {
                        'published': published,
                        'incentive': incentive,
                        'billed': billed
                    }
            
            elif field_def.data_type == 'currency':
                shipment[field_name] = self._parse_currency(match.group(1))
            
            elif field_def.data_type == 'float':
                shipment[field_name] = self._parse_float(match.group(1))
            
            elif field_def.data_type == 'integer':
                shipment[field_name] = self._parse_integer(match.group(1))
            
            elif field_def.data_type == 'date':
                shipment[field_name] = self._parse_date(match.group(1))
            
            else:  # string
                value = match.group(1).strip()
                if len(value) > 0:
                    shipment[field_name] = value
        
        except Exception as e:
            logger.warning(f"Error extracting {field_name}: {e}")
    
    def _post_process_shipment_data(self, shipment: Dict):
        """Post-process extracted data for accuracy and completeness"""
        
        # Clean service type
        if shipment.get('service_type'):
            service = shipment['service_type']
            # Remove trailing digits that might be ZIP codes
            service = re.sub(r'\s+\d{5}\s*', '', service)
            # Clean up extra whitespace
            service = ' '.join(service.split())
            shipment['service_type'] = service
        
        # Ensure tracking number format
        if shipment.get('tracking_number'):
            tracking = shipment['tracking_number']
            if not tracking.startswith('1Z') or len(tracking) != 18:
                # Try to find a valid tracking number in the string
                tracking_match = re.search(r'1Z[A-Z0-9]{16}', str(tracking))
                if tracking_match:
                    shipment['tracking_number'] = tracking_match.group()
        
        # Validate ZIP codes
        if shipment.get('destination_zip'):
            zip_code = str(shipment['destination_zip'])
            if not re.match(r'^\d{5}(-\d{4})?', zip_code):
                # Try to extract valid ZIP
                zip_match = re.search(r'\d{5}(?:-\d{4})?', zip_code)
                if zip_match:
                    shipment['destination_zip'] = zip_match.group()
        
        # Parse customer weight if available
        if not shipment.get('customer_weight'):
            weight_match = re.search(r'Customer\s+Weight\s+([\d.]+)', str(shipment))
            if weight_match:
                shipment['customer_weight'] = self._parse_float(weight_match.group(1))
        
        # Extract dimensions if available
        if not shipment.get('dimensions'):
            dim_patterns = [
                r'Customer\s+Entered\s+Dimensions\s*=\s*([^\n]+)',
                r'Dimensions\s*=\s*([^\n]+)',
                r'(\d+\s*x\s*\d+\s*x\s*\d+\s*in)'
            ]
            
            for pattern in dim_patterns:
                match = re.search(pattern, str(shipment), re.IGNORECASE)
                if match:
                    shipment['dimensions'] = match.group(1).strip()
                    break
        
        # Extract message codes
        if not shipment.get('message_codes'):
            msg_match = re.search(r'Message\s+Codes?:?\s*([a-z0-9\s,]+)', str(shipment), re.IGNORECASE)
            if msg_match:
                shipment['message_codes'] = msg_match.group(1).strip()
    
    def _parse_currency(self, value: str) -> Optional[float]:
        """Enhanced currency parsing"""
        if not value:
            return None
        try:
            # Handle negative values
            cleaned = str(value).replace(',', '').replace('', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Enhanced float parsing"""
        if not value:
            return None
        try:
            cleaned = str(value).replace(',', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _parse_integer(self, value: str) -> Optional[int]:
        """Enhanced integer parsing"""
        if not value:
            return None
        try:
            cleaned = str(value).replace(',', '').strip()
            return int(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _parse_date(self, value: str, invoice_year: int = None) -> Optional[str]:
        """Enhanced date parsing"""
        if not value:
            return None
        
        try:
            # Handle MM/DD format
            if re.match(r'\d{1,2}/\d{1,2}', value):
                month, day = value.split('/')
                year = invoice_year or datetime.now().year
                return f"{year}-{int(month):02d}-{int(day):02d}"
            
            # Handle MM/DD/YYYY format
            elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', value):
                month, day, year = value.split('/')
                if len(year) == 2:
                    year = 2000 + int(year)
                return f"{int(year)}-{int(month):02d}-{int(day):02d}"
            
            # Handle full date formats
            else:
                return value.strip()
                
        except (ValueError, IndexError):
            return value.strip()
    
    def _clean_service_name(self, service: str) -> str:
        """Clean service name"""
        if not service:
            return None
        
        # Remove trailing ZIP codes and numbers
        service = re.sub(r'\s+\d{5}\s*', '', service)
        service = re.sub(r'\s+\d{1,4}\s*', '', service)
        
        # Clean up whitespace
        service = ' '.join(service.split())
        
        return service.strip()
    
    def _is_valid_address(self, address: str) -> bool:
        """Validate if extracted text is a valid address"""
        if not address or len(address) < 5:
            return False
        
        # Should start with a number and contain address keywords
        address_indicators = ['street', 'st', 'avenue', 'ave', 'drive', 'dr', 'road', 'rd', 'court', 'ct', 'boulevard', 'blvd', 'lane', 'ln']
        
        return (address[0].isdigit() and 
                any(indicator in address.lower() for indicator in address_indicators))
    
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
 