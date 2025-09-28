import fitz  # PyMuPDF
from PIL import Image
import io
from typing import List, Tuple, Dict, Any
import re

class PDFTextExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
    
    def extract_page_data(self, page_num: int) -> Tuple[Image.Image, List[str], List[List[int]]]:
        """
        Extract image, words, and bounding boxes from a PDF page
        Enhanced for matrix-based extraction
        Returns: (image, words, boxes)
        """
        page = self.doc[page_num]
        
        # Convert page to image with higher resolution for better OCR
        mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # Extract text with enhanced coordinate information
        words, boxes = self._extract_structured_text(page)
        
        return image, words, boxes
    
    def _extract_structured_text(self, page) -> Tuple[List[str], List[List[int]]]:
        """
        Extract text with precise coordinate information for matrix parsing
        """
        # Get text dictionary with detailed positioning
        text_dict = page.get_text("dict")
        
        # Extract words with coordinates and structure them
        structured_data = self._process_text_blocks(text_dict)
        
        # Convert to the format expected by the invoice parser
        words = []
        boxes = []
        
        for item in structured_data:
            words.append(item['text'])
            boxes.append([
                int(item['bbox'][0]), 
                int(item['bbox'][1]), 
                int(item['bbox'][2]), 
                int(item['bbox'][3])
            ])
        
        return words, boxes
    
    def _process_text_blocks(self, text_dict: dict) -> List[Dict[str, Any]]:
        """
        Process text blocks and extract structured data for matrix parsing
        """
        structured_items = []
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                block_items = self._process_text_block(block)
                structured_items.extend(block_items)
        
        # Sort by vertical position (top to bottom), then horizontal (left to right)
        structured_items.sort(key=lambda x: (x['bbox'][1], x['bbox'][0]))
        
        return structured_items
    
    def _process_text_block(self, block: dict) -> List[Dict[str, Any]]:
        """Process individual text block and extract meaningful units"""
        items = []
        
        for line in block.get("lines", []):
            line_items = self._process_text_line(line)
            items.extend(line_items)
        
        return items
    
    def _process_text_line(self, line: dict) -> List[Dict[str, Any]]:
        """Process text line and extract words with positioning"""
        items = []
        line_bbox = line.get("bbox", [0, 0, 0, 0])
        
        # Collect all spans in this line
        line_text_parts = []
        all_spans = []
        
        for span in line.get("spans", []):
            span_text = span.get("text", "").strip()
            if span_text:
                line_text_parts.append(span_text)
                all_spans.append(span)
        
        if not line_text_parts:
            return items
        
        # Create line-level item for matrix parsing
        full_line_text = " ".join(line_text_parts)
        
        # Check if this looks like a shipment data line
        if self._is_shipment_data_line(full_line_text):
            # For shipment lines, extract individual fields with their positions
            field_items = self._extract_shipment_fields(full_line_text, line_bbox, all_spans)
            items.extend(field_items)
        else:
            # For other lines, keep as single unit
            items.append({
                'text': full_line_text,
                'bbox': line_bbox,
                'type': 'line',
                'font_info': self._get_font_info(all_spans[0]) if all_spans else {}
            })
        
        return items
    
    def _is_shipment_data_line(self, text: str) -> bool:
        """Check if line contains shipment data matrix information"""
        # Look for patterns that indicate shipment data
        patterns = [
            r'\d{2}/\d{2}\s+1Z[A-Z0-9]+',  # Date + tracking number
            r'Residential\s+Surcharge',     # Surcharge lines
            r'Fuel\s+Surcharge',
            r'Delivery\s+Area\s+Surcharge',
            r'Customer\s+Weight',
            r'Total\s+[\d,]+\.\d{2}',      # Total lines
            r'1st\s+ref:|2nd\s+ref:|UserID:', # Reference fields
            r'Sender:|Receiver:',           # Address fields
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    def _extract_shipment_fields(self, line_text: str, line_bbox: List[float], spans: List[dict]) -> List[Dict[str, Any]]:
        """Extract individual fields from shipment data lines with precise positioning"""
        items = []
        
        # Define field extraction patterns with their expected positions
        field_patterns = [
            ('date', r'(\d{2}/\d{2})'),
            ('tracking', r'(1Z[A-Z0-9]{16})'),
            ('service', r'(Ground|Air|Express|Standard|Select|Residential)'),
            ('zip', r'(\d{5}(?:-\d{4})?)'),
            ('zone', r'Zone\s*(\d{1,3})|\b(\d{1,3})\s*(?=\s*[\d,]+\.\d{2})'),
            ('weight', r'(\d+(?:\.\d+)?)\s*(?:lb|lbs)?'),
            ('currency', r'([\d,]+\.\d{2})'),
            ('reference', r'(\d+(?:st|nd|rd|th)\s+ref:[^\s]+)'),
            ('user_id', r'(UserID:[^\s]+)'),
            ('address_field', r'(Sender:|Receiver:)'),
        ]
        
        # Try to match and extract positioned fields
        for field_type, pattern in field_patterns:
            matches = list(re.finditer(pattern, line_text, re.IGNORECASE))
            for match in matches:
                # Estimate position within the line
                char_start = match.start()
                char_end = match.end()
                
                # Calculate approximate bbox based on character position
                line_width = line_bbox[2] - line_bbox[0]
                text_length = len(line_text)
                
                if text_length > 0:
                    field_x_start = line_bbox[0] + (char_start / text_length) * line_width
                    field_x_end = line_bbox[0] + (char_end / text_length) * line_width
                    
                    field_bbox = [
                        field_x_start,
                        line_bbox[1],
                        field_x_end,
                        line_bbox[3]
                    ]
                else:
                    field_bbox = line_bbox
                
                items.append({
                    'text': match.group(1) if match.groups() else match.group(0),
                    'bbox': field_bbox,
                    'type': field_type,
                    'line_text': line_text,
                    'match_span': (char_start, char_end)
                })
        
        # If no specific fields found, add the whole line
        if not items:
            items.append({
                'text': line_text,
                'bbox': line_bbox,
                'type': 'unknown_shipment_data',
                'font_info': self._get_font_info(spans[0]) if spans else {}
            })
        
        return items
    
    def _get_font_info(self, span: dict) -> Dict[str, Any]:
        """Extract font information from span"""
        return {
            'font': span.get('font', ''),
            'size': span.get('size', 0),
            'flags': span.get('flags', 0),
            'color': span.get('color', 0)
        }
    
    def extract_invoice_groups(self) -> List[Dict[str, Any]]:
        """
        Extract and group pages into individual invoices
        Returns list of invoice groups with their page ranges
        """
        groups = []
        current_group = None
        current_pages = []
        
        total_pages = self.get_total_pages()
        
        for page_num in range(total_pages):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Skip consolidated summary pages
            if any(keyword in text for keyword in ["Consolidated Billing Summary", "Consolidated Remittance Summary"]):
                continue
            
            # Check if this is the start of a new invoice
            if self._is_invoice_start_page(text):
                # Save previous group if exists
                if current_group is not None and current_pages:
                    groups.append({
                        'invoice_header': current_group,
                        'page_range': (current_pages[0], current_pages[-1]),
                        'page_count': len(current_pages),
                        'pages': current_pages.copy()
                    })
                
                # Start new group
                current_group = self._extract_invoice_header_info(text)
                current_pages = [page_num]
            else:
                # Continue current group
                if current_group is not None:
                    current_pages.append(page_num)
        
        # Don't forget the last group
        if current_group is not None and current_pages:
            groups.append({
                'invoice_header': current_group,
                'page_range': (current_pages[0], current_pages[-1]),
                'page_count': len(current_pages),
                'pages': current_pages.copy()
            })
        
        return groups
    
    def _is_invoice_start_page(self, text: str) -> bool:
        """Check if page is the start of a new invoice"""
        return (
            re.search(r'Delivery Service Invoice', text, re.IGNORECASE) and
            re.search(r'Page\s+1\s+of\s+\d+', text, re.IGNORECASE)
        )
    
    def _extract_invoice_header_info(self, text: str) -> Dict[str, str]:
        """Extract basic header information from invoice start page"""
        header = {}
        
        # Extract key fields
        patterns = {
            'invoice_number': r'Invoice\s+Number\s+([A-Z0-9\-]+)',
            'account_number': r'Account\s+Number\s+([A-Z0-9\-]+)',
            'control_id': r'Control\s+ID\s+([A-Z0-9\-#]+)',
            'invoice_date': r'Invoice\s+Date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            'shipped_from': r'Shipped\s+from:\s*([^\n]+)'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header[field] = match.group(1).strip()
        
        return header
    
    def get_total_pages(self) -> int:
        """Get total number of pages in PDF"""
        return len(self.doc)
    
    def is_empty_page(self, page_num: int) -> bool:
        """Check if page is empty or has minimal content"""
        page = self.doc[page_num]
        text = page.get_text().strip()
        
        # Consider page empty if it has very little text
        if len(text) < 50:
            return True
        
        # Check for pages with only headers/footers
        lines = text.split('\n')
        meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        return len(meaningful_lines) < 3
    
    def close(self):
        """Close the PDF document"""
        self.doc.close()