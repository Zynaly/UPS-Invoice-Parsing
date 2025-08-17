import fitz  # PyMuPDF
from PIL import Image
import io
from typing import List, Tuple

class PDFTextExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
    
    def extract_page_data(self, page_num: int) -> Tuple[Image.Image, List[str], List[List[int]]]:
        """
        Extract image, words, and bounding boxes from a PDF page
        Returns: (image, words, boxes)
        """
        page = self.doc[page_num]
        
        # Convert page to image
        mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # Extract text with coordinates
        text_dict = page.get_text("dict")
        words, boxes = self._extract_words_and_boxes(text_dict)
        
        return image, words, boxes
    
    def _extract_words_and_boxes(self, text_dict: dict) -> Tuple[List[str], List[List[int]]]:
        """Extract words and bounding boxes from text dictionary"""
        words = []
        boxes = []
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            bbox = span["bbox"]
                            words.append(text)
                            boxes.append([int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])])
        
        return words, boxes
    
    def get_total_pages(self) -> int:
        """Get total number of pages in PDF"""
        return len(self.doc)
    
    def is_empty_page(self, page_num: int) -> bool:
        """Check if page is empty or has minimal content"""
        _, words, _ = self.extract_page_data(page_num)
        return len(words) < 5
    
    def close(self):
        """Close the PDF document"""
        self.doc.close()