import pandas as pd
import logging
from pathlib import Path
from text_extractor import PDFTextExtractor
from invoice_parser import InvoiceParser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(pdf_path: str, output_csv: str = "extracted_invoices.csv"):
    """
    Main function to extract invoice data from PDF and save to CSV
    """
    logger.info(f"Starting invoice extraction from: {pdf_path}")
    
    # Initialize components
    extractor = PDFTextExtractor(pdf_path)
    parser = InvoiceParser()
    
    extracted_data = []
    total_pages = extractor.get_total_pages()
    
    logger.info(f"Processing {total_pages} pages...")
    
    try:
        for page_num in range(total_pages):
            logger.info(f"Processing page {page_num + 1}/{total_pages}")
            
            # Check if page is empty
            if extractor.is_empty_page(page_num):
                logger.info(f"Page {page_num + 1}: Empty page, skipping")
                continue
            
            # Extract text and layout data
            image, words, boxes = extractor.extract_page_data(page_num)
            
            # Parse invoice data (now returns list of shipments)
            shipments_data = parser.parse_invoice(image, words, boxes)
            
            if shipments_data:
                for shipment in shipments_data:
                    shipment['page_number'] = page_num + 1
                    extracted_data.append(shipment)
                
                logger.info(f"Page {page_num + 1}: {len(shipments_data)} shipments extracted")
                for i, shipment in enumerate(shipments_data):
                    logger.info(f"Shipment {i+1}: {shipment}")
            else:
                logger.info(f"Page {page_num + 1}: No invoice data found")
    
    except Exception as e:
        logger.error(f"Error processing pages: {e}")
    
    finally:
        extractor.close()
    
    # Save results to CSV
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        
        # Ensure all required columns exist
        required_columns = ['invoice_number', 'account_number', 'invoice_date', 'shipment_date', 'tracking_number', 'receiver_name', 'receiver_address', 'page_number']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Reorder columns
        df = df[required_columns]
        df.to_csv(output_csv, index=False)
        
        logger.info(f"Extraction completed!")
        logger.info(f"Total shipments found: {len(extracted_data)}")
        logger.info(f"Results saved to: {output_csv}")
        
        # Print summary
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total pages processed: {total_pages}")
        print(f"Total shipments found: {len(extracted_data)}")
        print(f"Output file: {output_csv}")
        
        # Show sample data
        if len(df) > 0:
            print(f"\nSample extracted data:")
            print(df.head().to_string(index=False))
    else:
        logger.warning("No invoice data extracted from any page")
        print("No shipments found in the PDF")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <pdf_path> [output_csv]")
        print("Example: python main.py invoices.pdf extracted_data.csv")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "extracted_invoices.csv"
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF file '{pdf_path}' not found")
        sys.exit(1)
    
    main(pdf_path, output_csv)