# # import torch
# # from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
# # from PIL import Image
# # import re
# # from typing import List, Dict, Optional
# # from datetime import datetime

# # class InvoiceParser:
# #     def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
# #         """Initialize LayoutLMv3 model for invoice parsing"""
# #         self.processor = LayoutLMv3Processor.from_pretrained(model_name)
# #         self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
    
# #     def is_invoice_page(self, words: List[str]) -> bool:
# #         """Check if page contains invoice data"""
# #         text_lower = ' '.join(words).lower()
# #         indicators = ['delivery service invoice', 'invoice', 'tracking number', 'account number']
# #         return any(indicator in text_lower for indicator in indicators)
    
# #     def parse_invoice(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
# #         """
# #         Parse invoice data from image, words, and boxes
# #         Returns list of extracted data (multiple shipments per page)
# #         """
# #         if not self.is_invoice_page(words):
# #             return []
        
# #         try:
# #             # Try LayoutLMv3 extraction first
# #             data_list = self._extract_with_layoutlmv3(image, words, boxes)
# #             if not data_list:
# #                 # Fallback to rule-based extraction
# #                 data_list = self._extract_rule_based(words)
# #             return data_list
# #         except Exception as e:
# #             print(f"Error in parsing: {e}")
# #             return self._extract_rule_based(words)
    
# #     def _extract_with_layoutlmv3(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
# #         """Extract using LayoutLMv3 model"""
# #         try:
# #             encoding = self.processor(image, words, boxes=boxes, return_tensors="pt", 
# #                                     truncation=True, padding=True, max_length=512)
            
# #             with torch.no_grad():
# #                 outputs = self.model(**encoding)
# #                 # For now, fallback to rule-based as model needs specific training
# #                 return self._extract_rule_based(words)
                
# #         except Exception as e:
# #             print(f"LayoutLMv3 failed: {e}")
# #             return self._extract_rule_based(words)
    
# #     def _extract_rule_based(self, words: List[str]) -> List[Dict[str, str]]:
# #         """Rule-based extraction for UPS invoices - extracts ALL shipments from page"""
# #         text = ' '.join(words)
        
# #         # Extract common invoice-level data (same for all shipments on page)
# #         common_data = self._extract_common_invoice_data(text)
        
# #         # Extract individual shipment data
# #         shipments = self._extract_all_shipments(text)
        
# #         # Combine common data with each shipment
# #         result_list = []
# #         for shipment in shipments:
# #             combined_data = {**common_data, **shipment}
# #             result_list.append(combined_data)
        
# #         return result_list if result_list else []
    
# #     def _extract_common_invoice_data(self, text: str) -> Dict[str, str]:
# #         """Extract invoice-level data that's common to all shipments"""
# #         common_data = {}
        
# #         # Extract Invoice Number
# #         invoice_patterns = [
# #             r'Invoice\s+Number\s+([A-Z0-9]+)',
# #             r'Invoice\s+Date.*?Invoice\s+Number\s+([A-Z0-9]+)',
# #             r'([0-9A-Z]{10,})\s*(?=.*Account\s+Number)'
# #         ]
# #         for pattern in invoice_patterns:
# #             match = re.search(pattern, text, re.IGNORECASE)
# #             if match:
# #                 common_data['invoice_number'] = match.group(1).strip()
# #                 break
        
# #         # Extract Account Number  
# #         account_patterns = [
# #             r'Account\s+Number\s+([A-Z0-9]+)',
# #             r'Account\s+([A-Z0-9]{4,})',
# #         ]
# #         for pattern in account_patterns:
# #             match = re.search(pattern, text, re.IGNORECASE)
# #             if match:
# #                 common_data['account_number'] = match.group(1).strip()
# #                 break
        
# #         # Extract Invoice Date
# #         date_patterns = [
# #             r'Invoice\s+Date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
# #             r'Invoice\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})',
# #             r'Invoice\s+Date\s+(\d{4}-\d{2}-\d{2})',
# #             r'(August\s+\d{1,2},\s+\d{4}|July\s+\d{1,2},\s+\d{4}|September\s+\d{1,2},\s+\d{4})'
# #         ]
# #         for pattern in date_patterns:
# #             match = re.search(pattern, text, re.IGNORECASE)
# #             if match:
# #                 common_data['invoice_date'] = match.group(1).strip()
# #                 break
        
# #         return common_data
    
# #     def _extract_all_shipments(self, text: str) -> List[Dict[str, str]]:
# #         """Extract all individual shipments from the page"""
# #         shipments = []
        
# #         # Split text by shipment sections - look for date patterns that start new sections
# #         date_pattern = r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})'
# #         sections = re.split(date_pattern, text)
        
# #         # Alternative approach: Find all tracking numbers and their associated data
# #         tracking_pattern = r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})\s+([^1Z]+?)(?=\d{2}/\d{2}\s+1Z|$)'
# #         matches = re.finditer(tracking_pattern, text, re.DOTALL)
        
# #         for match in matches:
# #             shipment_date = match.group(1)
# #             tracking_number = match.group(2)
# #             shipment_text = match.group(3)
            
# #             shipment_data = {
# #                 'shipment_date': shipment_date,
# #                 'tracking_number': tracking_number
# #             }
            
# #             # Extract receiver info from this shipment section
# #             receiver_data = self._extract_receiver_from_section(shipment_text)
# #             shipment_data.update(receiver_data)
            
# #             shipments.append(shipment_data)
        
# #         # Fallback: if no matches found, try simpler approach
# #         if not shipments:
# #             shipments = self._extract_shipments_fallback(text)
        
# #         return shipments
    
# #     def _extract_receiver_from_section(self, section_text: str) -> Dict[str, str]:
# #         """Extract receiver information from a shipment section"""
# #         receiver_data = {}
        
# #         # Look for "Receiver:" pattern
# #         receiver_match = re.search(r'Receiver:\s*([A-Z\s]+?)\s+([A-Z0-9\s,.-]+?)(?=\s+[A-Z]{2}\s+\d{5})', section_text, re.IGNORECASE)
# #         if receiver_match:
# #             receiver_data['receiver_name'] = receiver_match.group(1).strip()
# #             # Extract full address
# #             addr_match = re.search(r'Receiver:\s*[A-Z\s]+?\s+(.+?)(?=\s+(?:1st ref|UserID|Sender|$))', section_text, re.IGNORECASE | re.DOTALL)
# #             if addr_match:
# #                 receiver_data['receiver_address'] = ' '.join(addr_match.group(1).split())
# #         else:
# #             # Try to find common names from your sample
# #             name_patterns = [
# #                 r'(CLAIRE SAFFIAN|TAYLOR MITCHEM|MAUREEN QUERN)',
# #                 r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]+)?)'  # General name pattern
# #             ]
            
# #             for pattern in name_patterns:
# #                 name_match = re.search(pattern, section_text)
# #                 if name_match:
# #                     receiver_data['receiver_name'] = name_match.group(1)
                    
# #                     # Try to extract address after the name
# #                     addr_patterns = [
# #                         rf'{re.escape(name_match.group(1))}\s+(.+?)(?=\s+[A-Z]{{2}}\s+\d{{5}})',
# #                         r'(\d+\s+[A-Z\s]+(?:AVE|AVENUE|ST|STREET|DRIVE|DR|CT).*?[A-Z]{2}\s+\d{5}(?:-\d{4})?)'
# #                     ]
                    
# #                     for addr_pattern in addr_patterns:
# #                         addr_match = re.search(addr_pattern, section_text, re.IGNORECASE)
# #                         if addr_match:
# #                             receiver_data['receiver_address'] = ' '.join(addr_match.group(1).split())
# #                             break
# #                     break
        
# #         return receiver_data
    
# #     def _extract_shipments_fallback(self, text: str) -> List[Dict[str, str]]:
# #         """Fallback method to extract shipments"""
# #         shipments = []
        
# #         # Find all tracking numbers with their dates
# #         tracking_matches = re.finditer(r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})', text)
        
# #         for match in tracking_matches:
# #             shipment_date = match.group(1)
# #             tracking_number = match.group(2)
            
# #             shipment_data = {
# #                 'shipment_date': shipment_date,
# #                 'tracking_number': tracking_number,
# #                 'receiver_name': '',
# #                 'receiver_address': ''
# #             }
            
# #             shipments.append(shipment_data)
        
# #         # If we found tracking numbers, try to match them with receivers
# #         if shipments:
# #             # Look for all receiver patterns
# #             receiver_patterns = [
# #                 r'Receiver:\s*([A-Z\s]+?)\s+([A-Z0-9\s,.-]+?)(?=Receiver:|$)',
# #                 r'(CLAIRE SAFFIAN|TAYLOR MITCHEM|MAUREEN QUERN)\s+([A-Z0-9\s,.-]+?)(?=(?:CLAIRE|TAYLOR|MAUREEN|\d{2}/\d{2}|$))'
# #             ]
            
# #             receivers = []
# #             for pattern in receiver_patterns:
# #                 matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
# #                 for match in matches:
# #                     receivers.append({
# #                         'receiver_name': match.group(1).strip(),
# #                         'receiver_address': ' '.join(match.group(2).split()) if len(match.groups()) > 1 else ''
# #                     })
            
# #             # Match receivers to shipments (assume same order)
# #             for i, shipment in enumerate(shipments):
# #                 if i < len(receivers):
# #                     shipment.update(receivers[i])
        
# #         return shipments






















# import torch
# from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
# from PIL import Image
# import re
# from typing import List, Dict, Optional
# from datetime import datetime

# class InvoiceParser:
#     def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
#         """Initialize LayoutLMv3 model for invoice parsing"""
#         self.processor = LayoutLMv3Processor.from_pretrained(model_name)
#         self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
    
#     def is_invoice_page(self, words: List[str]) -> bool:
#         """Check if page contains invoice data"""
#         text_lower = ' '.join(words).lower()
#         indicators = ['delivery service invoice', 'invoice', 'tracking number', 'account number']
#         return any(indicator in text_lower for indicator in indicators)
    
#     def parse_invoice(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
#         """
#         Parse invoice data from image, words, and boxes
#         Returns list of extracted data (multiple shipments per page)
#         """
#         if not self.is_invoice_page(words):
#             return []
        
#         try:
#             # Try LayoutLMv3 extraction first
#             data_list = self._extract_with_layoutlmv3(image, words, boxes)
#             if not data_list:
#                 # Fallback to rule-based extraction
#                 data_list = self._extract_rule_based(words)
#             return data_list
#         except Exception as e:
#             print(f"Error in parsing: {e}")
#             return self._extract_rule_based(words)
    
#     def _extract_with_layoutlmv3(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
#         """Extract using LayoutLMv3 model"""
#         try:
#             encoding = self.processor(image, words, boxes=boxes, return_tensors="pt", 
#                                     truncation=True, padding=True, max_length=512)
            
#             with torch.no_grad():
#                 outputs = self.model(**encoding)
#                 # For now, fallback to rule-based as model needs specific training
#                 return self._extract_rule_based(words)
                
#         except Exception as e:
#             print(f"LayoutLMv3 failed: {e}")
#             return self._extract_rule_based(words)
    
#     def _extract_rule_based(self, words: List[str]) -> List[Dict[str, str]]:
#         """Rule-based extraction for UPS invoices - extracts ALL shipments from page"""
#         text = ' '.join(words)
        
#         # Extract common invoice-level data (same for all shipments on page)
#         common_data = self._extract_common_invoice_data(text)
        
#         # Extract individual shipment data
#         shipments = self._extract_all_shipments(text)
        
#         # Combine common data with each shipment
#         result_list = []
#         for shipment in shipments:
#             combined_data = {**common_data, **shipment}
#             result_list.append(combined_data)
        
#         return result_list if result_list else []
    
#     def _extract_common_invoice_data(self, text: str) -> Dict[str, str]:
#         """Extract invoice-level data that's common to all shipments"""
#         common_data = {}
        
#         # Extract Invoice Number
#         invoice_patterns = [
#             r'Invoice\s+Number\s+([A-Z0-9]+)',
#             r'Invoice\s+Date.*?Invoice\s+Number\s+([A-Z0-9]+)',
#             r'([0-9A-Z]{10,})\s*(?=.*Account\s+Number)'
#         ]
#         for pattern in invoice_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 common_data['invoice_number'] = match.group(1).strip()
#                 break
        
#         # Extract Account Number  
#         account_patterns = [
#             r'Account\s+Number\s+([A-Z0-9]+)',
#             r'Account\s+([A-Z0-9]{4,})',
#         ]
#         for pattern in account_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 common_data['account_number'] = match.group(1).strip()
#                 break
        
#         # Extract Invoice Date
#         date_patterns = [
#             r'Invoice\s+Date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
#             r'Invoice\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})',
#             r'Invoice\s+Date\s+(\d{4}-\d{2}-\d{2})',
#             r'(August\s+\d{1,2},\s+\d{4}|July\s+\d{1,2},\s+\d{4}|September\s+\d{1,2},\s+\d{4})'
#         ]
#         for pattern in date_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 common_data['invoice_date'] = match.group(1).strip()
#                 break
        
#         return common_data
    
#     def _extract_all_shipments(self, text: str) -> List[Dict[str, str]]:
#         """Extract all individual shipments from the page"""
#         shipments = []
        
#         # Debug: Print text to see what we're working with
#         print(f"DEBUG: Extracting from text length: {len(text)}")
        
#         # Method 1: Find tracking numbers and extract surrounding context
#         tracking_pattern = r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})'
#         tracking_matches = list(re.finditer(tracking_pattern, text))
        
#         print(f"DEBUG: Found {len(tracking_matches)} tracking numbers")
        
#         for i, match in enumerate(tracking_matches):
#             shipment_date = match.group(1)
#             tracking_number = match.group(2)
            
#             # Get text section for this shipment
#             start_pos = match.start()
            
#             # Find end position (start of next tracking number or end of text)
#             if i + 1 < len(tracking_matches):
#                 end_pos = tracking_matches[i + 1].start()
#             else:
#                 end_pos = len(text)
            
#             shipment_section = text[start_pos:end_pos]
#             print(f"DEBUG: Shipment section {i+1}: {shipment_section[:200]}...")
            
#             shipment_data = {
#                 'shipment_date': shipment_date,
#                 'tracking_number': tracking_number
#             }
            
#             # Extract receiver info from this specific section
#             receiver_data = self._extract_receiver_from_section(shipment_section)
#             shipment_data.update(receiver_data)
            
#             print(f"DEBUG: Extracted receiver data: {receiver_data}")
#             shipments.append(shipment_data)
        
#         # Method 2: If above didn't work well, try looking for "Receiver:" patterns directly
#         if not shipments or all(not s.get('receiver_name') for s in shipments):
#             print("DEBUG: Trying alternative receiver extraction method")
#             shipments = self._extract_shipments_alternative(text)
        
#         return shipments
    
#     def _extract_receiver_from_section(self, section_text: str) -> Dict[str, str]:
#         """Extract receiver information from a shipment section"""
#         receiver_data = {
#             'receiver_name': '',
#             'receiver_address': ''
#         }
        
#         # Look for "Receiver:" pattern first
#         receiver_match = re.search(r'Receiver:\s*([A-Z\s]+?)\s+([A-Z0-9\s,.-]+?)(?=\s+[A-Z]{2}\s+\d{5})', section_text, re.IGNORECASE)
#         if receiver_match:
#             receiver_data['receiver_name'] = receiver_match.group(1).strip()
#             # Extract full address
#             addr_match = re.search(r'Receiver:\s*[A-Z\s]+?\s+(.+?)(?=\s+(?:1st ref|UserID|Sender|$))', section_text, re.IGNORECASE | re.DOTALL)
#             if addr_match:
#                 receiver_data['receiver_address'] = ' '.join(addr_match.group(1).split())
#         else:
#             # Try alternative patterns for name extraction
#             name_patterns = [
#                 r'(CLAIRE SAFFIAN|TAYLOR MITCHEM|MAUREEN QUERN)',
#                 r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]+)?)',  # General name pattern
#                 r'Next Day Air Residential.*?\n([A-Z\s]+)',  # After service type
#                 r'Ground Residential.*?\n([A-Z\s]+)'  # After service type
#             ]
            
#             for pattern in name_patterns:
#                 name_match = re.search(pattern, section_text, re.IGNORECASE | re.MULTILINE)
#                 if name_match:
#                     potential_name = name_match.group(1).strip()
#                     # Filter out service types and common non-name text
#                     if not re.match(r'(Customer|Weight|Residential|Surcharge|Fuel|Dimensions|Total|UserID|Sender)', potential_name, re.IGNORECASE):
#                         receiver_data['receiver_name'] = potential_name
#                         break
            
#             # Try to extract address even if name not found
#             addr_patterns = [
#                 r'(\d+\s+[A-Z\s]+(?:AVE|AVENUE|ST|STREET|DRIVE|DR|CT|RD|ROAD|BLVD|BOULEVARD|LANE|LN).*?[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
#                 r'([A-Z0-9\s,.-]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)',  # General address pattern
#                 r'Receiver:\s*[^\n]*\n([A-Z0-9\s,.-]+)',  # Line after Receiver:
#             ]
            
#             for addr_pattern in addr_patterns:
#                 addr_match = re.search(addr_pattern, section_text, re.IGNORECASE | re.MULTILINE)
#                 if addr_match:
#                     potential_addr = ' '.join(addr_match.group(1).split())
#                     # Filter out non-address text
#                     if not re.match(r'(Customer|Weight|Residential|Surcharge|Fuel|Dimensions|Total)', potential_addr, re.IGNORECASE):
#                         receiver_data['receiver_address'] = potential_addr
#                         break
        
#         return receiver_data
    
#     def _extract_shipments_alternative(self, text: str) -> List[Dict[str, str]]:
#         """Alternative method to extract shipments with better receiver matching"""
#         shipments = []
        
#         # First, find all tracking numbers with dates
#         tracking_pattern = r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})'
#         tracking_matches = re.finditer(tracking_pattern, text)
        
#         # Then find all receiver patterns
#         receiver_patterns = [
#             r'Receiver:\s*([A-Z\s]+?)\s+(.+?)(?=(?:Receiver:|1st ref:|UserID:|Sender:|$))',
#             r'(CLAIRE SAFFIAN|TAYLOR MITCHEM|MAUREEN QUERN|[A-Z]{3,}\s+[A-Z]{3,})\s+(.+?)(?=(?:CLAIRE|TAYLOR|MAUREEN|[A-Z]{3,}\s+[A-Z]{3,}|\d{2}/\d{2}|$))'
#         ]
        
#         receivers = []
#         for pattern in receiver_patterns:
#             matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
#             for match in matches:
#                 name = match.group(1).strip()
#                 address = ' '.join(match.group(2).split()) if len(match.groups()) > 1 else ''
                
#                 # Clean up address - remove non-address content
#                 address = re.sub(r'\s+(Customer Weight|Residential Surcharge|Fuel Surcharge|Total|1st ref:|UserID:).*', '', address, flags=re.IGNORECASE)
#                 address = re.sub(r'\s*\d+\.\d+\s*-?\d*\.\d*\s*\d+\.\d+\s*', ' ', address)  # Remove price numbers
                
#                 receivers.append({
#                     'receiver_name': name,
#                     'receiver_address': address.strip()
#                 })
        
#         print(f"DEBUG: Found {len(receivers)} receivers")
#         for i, receiver in enumerate(receivers):
#             print(f"DEBUG: Receiver {i+1}: {receiver}")
        
#         # Match tracking numbers with receivers
#         tracking_list = [(match.group(1), match.group(2)) for match in re.finditer(tracking_pattern, text)]
        
#         for i, (date, tracking) in enumerate(tracking_list):
#             shipment_data = {
#                 'shipment_date': date,
#                 'tracking_number': tracking,
#                 'receiver_name': '',
#                 'receiver_address': ''
#             }
            
#             # Try to match with receiver (assume same order or closest match)
#             if i < len(receivers):
#                 shipment_data.update(receivers[i])
            
#             shipments.append(shipment_data)
        
#         return shipments
    

















import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import re
from typing import List, Dict, Optional
from datetime import datetime

class InvoiceParser:
    def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
        """Initialize LayoutLMv3 model for invoice parsing"""
        self.processor = LayoutLMv3Processor.from_pretrained(model_name)
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
    
    def is_invoice_page(self, words: List[str]) -> bool:
        """Check if page contains invoice data"""
        text_lower = ' '.join(words).lower()
        indicators = ['delivery service invoice', 'invoice', 'tracking number', 'account number']
        return any(indicator in text_lower for indicator in indicators)
    
    def parse_invoice(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
        """
        Parse invoice data from image, words, and boxes
        Returns list of extracted data (multiple shipments per page)
        """
        if not self.is_invoice_page(words):
            return []
        
        try:
            # Try LayoutLMv3 extraction first
            data_list = self._extract_with_layoutlmv3(image, words, boxes)
            if not data_list:
                # Fallback to rule-based extraction
                data_list = self._extract_rule_based(words)
            return data_list
        except Exception as e:
            print(f"Error in parsing: {e}")
            return self._extract_rule_based(words)
    
    def _extract_with_layoutlmv3(self, image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[Dict[str, str]]:
        """Extract using LayoutLMv3 model"""
        try:
            encoding = self.processor(image, words, boxes=boxes, return_tensors="pt", 
                                    truncation=True, padding=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**encoding)
                # For now, fallback to rule-based as model needs specific training
                return self._extract_rule_based(words)
                
        except Exception as e:
            print(f"LayoutLMv3 failed: {e}")
            return self._extract_rule_based(words)
    
    def _extract_rule_based(self, words: List[str]) -> List[Dict[str, str]]:
        """Rule-based extraction for UPS invoices - extracts ALL shipments from page"""
        text = ' '.join(words)
        
        print(f"DEBUG: Processing text of length {len(text)}")
        print(f"DEBUG: First 500 chars: {text[:500]}")
        
        # Extract common invoice-level data (same for all shipments on page)
        common_data = self._extract_common_invoice_data(text)
        print(f"DEBUG: Common data extracted: {common_data}")
        
        # Extract individual shipment data using improved method
        shipments = self._extract_all_shipments_improved(text)
        print(f"DEBUG: Found {len(shipments)} shipments")
        
        # Combine common data with each shipment
        result_list = []
        for i, shipment in enumerate(shipments):
            combined_data = {**common_data, **shipment}
            result_list.append(combined_data)
            print(f"DEBUG: Shipment {i+1}: {combined_data}")
        
        return result_list if result_list else []
    
    def _extract_common_invoice_data(self, text: str) -> Dict[str, str]:
        """Extract invoice-level data that's common to all shipments"""
        common_data = {}
        
        # Extract Invoice Number
        invoice_patterns = [
            r'Invoice\s+Number\s+([A-Z0-9]+)',
            r'Invoice\s+Date.*?Invoice\s+Number\s+([A-Z0-9]+)',
            r'([0-9A-Z]{10,})\s*(?=.*Account\s+Number)'
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                common_data['invoice_number'] = match.group(1).strip()
                break
        
        # Extract Account Number  
        account_patterns = [
            r'Account\s+Number\s+([A-Z0-9]+)',
            r'Account\s+([A-Z0-9]{4,})',
        ]
        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                common_data['account_number'] = match.group(1).strip()
                break
        
        # Extract Invoice Date
        date_patterns = [
            r'Invoice\s+Date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            r'Invoice\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'Invoice\s+Date\s+(\d{4}-\d{2}-\d{2})',
            r'(August\s+\d{1,2},\s+\d{4}|July\s+\d{1,2},\s+\d{4}|September\s+\d{1,2},\s+\d{4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                common_data['invoice_date'] = match.group(1).strip()
                break
        
        return common_data
    
    def _extract_all_shipments_improved(self, text: str) -> List[Dict[str, str]]:
        """Improved method to extract all shipments with complete data"""
        shipments = []
        
        # Step 1: Find all shipment blocks (date + tracking number + everything until next shipment)
        # Pattern to find shipment boundaries
        shipment_boundary_pattern = r'(\d{2}/\d{2})\s+(1Z[A-Z0-9]{16})'
        
        # Find all boundaries
        boundaries = list(re.finditer(shipment_boundary_pattern, text))
        print(f"DEBUG: Found {len(boundaries)} shipment boundaries")
        
        for i, boundary in enumerate(boundaries):
            shipment_date = boundary.group(1)
            tracking_number = boundary.group(2)
            
            # Define the text block for this shipment
            start_pos = boundary.start()
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1].start()
            else:
                end_pos = len(text)
            
            shipment_block = text[start_pos:end_pos]
            print(f"\nDEBUG: === SHIPMENT {i+1} ===")
            print(f"DEBUG: Date: {shipment_date}, Tracking: {tracking_number}")
            print(f"DEBUG: Block (first 200 chars): {shipment_block[:200]}...")
            
            # Extract receiver data from this block
            receiver_data = self._extract_receiver_data_comprehensive(shipment_block)
            
            shipment_data = {
                'shipment_date': shipment_date,
                'tracking_number': tracking_number,
                'receiver_name': receiver_data.get('receiver_name', ''),
                'receiver_address': receiver_data.get('receiver_address', '')
            }
            
            print(f"DEBUG: Extracted - Name: '{receiver_data.get('receiver_name', 'NOT_FOUND')}', Address: '{receiver_data.get('receiver_address', 'NOT_FOUND')}'")
            
            shipments.append(shipment_data)
        
        return shipments
    
    def _extract_receiver_data_comprehensive(self, block: str) -> Dict[str, str]:
        """Comprehensive receiver data extraction from a shipment block"""
        receiver_data = {'receiver_name': '', 'receiver_address': ''}
        
        # Clean the block - normalize whitespace
        block = ' '.join(block.split())
        
        print(f"DEBUG: Processing block: {block[:300]}...")
        
        # Method 1: Look for explicit "Receiver:" pattern
        receiver_patterns = [
            # Pattern: Receiver: NAME ADDRESS
            r'Receiver:\s*([A-Z][A-Z\s]+?)\s+(\d+\s+[A-Z0-9\s,.-]+?[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
            # Pattern: Receiver: NAME then address on next lines
            r'Receiver:\s*([A-Z][A-Z\s]{5,40}?)\s+((?:\d+\s+)?[A-Z0-9\s,.-]+)',
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                name = self._clean_name(match.group(1))
                address = self._clean_address(match.group(2))
                
                if len(name) > 3 and len(address) > 10:
                    receiver_data['receiver_name'] = name
                    receiver_data['receiver_address'] = address
                    print(f"DEBUG: Method 1 success - Name: '{name}', Address: '{address}'")
                    return receiver_data
        
        # Method 2: Look for name patterns followed by address patterns
        # Find potential names (2+ consecutive capitalized words)
        name_matches = re.finditer(r'\b([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})*)\b', block)
        
        for name_match in name_matches:
            potential_name = name_match.group(1)
            
            # Skip obvious non-names
            if re.match(r'^(DELIVERY|SERVICE|INVOICE|CUSTOMER|WEIGHT|RESIDENTIAL|SURCHARGE|FUEL|DIMENSIONS|TOTAL|USERIDS?|SENDER|RECEIVER|GROUND|NEXT|DAY|AIR|TRACKING|NUMBER|ACCOUNT|PAGE)(\s+\w+)*$', potential_name, re.IGNORECASE):
                continue
            
            # Look for address after this name
            # Get text after the name
            remaining_text = block[name_match.end():]
            
            # Look for address patterns in the remaining text
            address_patterns = [
                r'^\s*(\d+\s+[A-Z\s]+(?:AVE|AVENUE|ST|STREET|DRIVE|DR|CT|COURT|RD|ROAD|BLVD|BOULEVARD|LANE|LN|WAY|PLACE|PL)\s+[A-Z\s]*[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
                r'^\s*([A-Z0-9\s,.-]*\d+[A-Z0-9\s,.-]*[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
            ]
            
            for addr_pattern in address_patterns:
                addr_match = re.search(addr_pattern, remaining_text, re.IGNORECASE)
                if addr_match:
                    name = self._clean_name(potential_name)
                    address = self._clean_address(addr_match.group(1))
                    
                    if len(name) > 3 and len(address) > 10:
                        receiver_data['receiver_name'] = name
                        receiver_data['receiver_address'] = address
                        print(f"DEBUG: Method 2 success - Name: '{name}', Address: '{address}'")
                        return receiver_data
        
        # Method 3: Extract any address-like pattern and see if there's a name before it
        all_addresses = re.finditer(r'(\d+\s+[A-Z\s,.-]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)', block, re.IGNORECASE)
        
        for addr_match in all_addresses:
            address = self._clean_address(addr_match.group(1))
            
            # Look for name before this address
            text_before = block[:addr_match.start()]
            name_pattern = r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})*)\s*$'
            name_match = re.search(name_pattern, text_before)
            
            if name_match:
                name = self._clean_name(name_match.group(1))
                
                if len(name) > 3 and len(address) > 10:
                    receiver_data['receiver_name'] = name
                    receiver_data['receiver_address'] = address
                    print(f"DEBUG: Method 3 success - Name: '{name}', Address: '{address}'")
                    return receiver_data
        
        # Method 4: Last resort - just extract any name and any address separately
        if not receiver_data['receiver_name']:
            name_matches = re.findall(r'\b([A-Z]{3,}\s+[A-Z]{3,})\b', block)
            for name in name_matches:
                if not re.match(r'^(DELIVERY|SERVICE|INVOICE|CUSTOMER|WEIGHT|RESIDENTIAL|SURCHARGE|FUEL|DIMENSIONS|TOTAL|USERIDS?|SENDER|RECEIVER|GROUND|NEXT|DAY|AIR|TRACKING|NUMBER|ACCOUNT|PAGE)(\s+\w+)?$', name, re.IGNORECASE):
                    receiver_data['receiver_name'] = self._clean_name(name)
                    break
        
        if not receiver_data['receiver_address']:
            addr_matches = re.findall(r'(\d+\s+[A-Z\s,.-]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)', block, re.IGNORECASE)
            if addr_matches:
                receiver_data['receiver_address'] = self._clean_address(addr_matches[0])
        
        print(f"DEBUG: Method 4 (fallback) - Name: '{receiver_data.get('receiver_name', 'NOT_FOUND')}', Address: '{receiver_data.get('receiver_address', 'NOT_FOUND')}'")
        return receiver_data
    
    def _clean_name(self, name: str) -> str:
        """Clean and validate name"""
        if not name:
            return ''
        
        # Remove common non-name words and clean up
        name = re.sub(r'\s+(Customer|Weight|Residential|Surcharge|Fuel|Next|Day|Air|Ground|Total)', '', name, flags=re.IGNORECASE)
        name = ' '.join(name.split())  # Normalize whitespace
        
        return name.strip()
    
    def _clean_address(self, address: str) -> str:
        """Clean and validate address"""
        if not address:
            return ''
        
        # Remove prices and weights
        address = re.sub(r'\s*\d+\.\d+\s*-?\d*\.\d*\s*\d+\.\d+\s*', ' ', address)
        # Remove common invoice terms
        address = re.sub(r'\s+(Customer Weight|Residential Surcharge|Fuel Surcharge|Total|1st ref|UserID|Sender).*', '', address, flags=re.IGNORECASE)
        # Normalize whitespace
        address = ' '.join(address.split())
        
        return address.strip()