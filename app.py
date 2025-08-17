from flask import Flask, request, jsonify, send_file, render_template
import os
import pandas as pd
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import logging
from text_extractor import PDFTextExtractor
from invoice_parser import InvoiceParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload and process it"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
        
        # Save uploaded file
        file.save(pdf_path)
        logger.info(f"File uploaded: {pdf_path}")
        
        # Process the PDF
        result = process_pdf(pdf_path, unique_id)
        
        # Clean up uploaded file
        os.remove(pdf_path)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

def process_pdf(pdf_path, unique_id):
    """Process PDF and extract invoice data"""
    try:
        logger.info(f"Starting extraction for: {pdf_path}")
        
        # Initialize components
        extractor = PDFTextExtractor(pdf_path)
        parser = InvoiceParser()
        
        extracted_data = []
        total_pages = extractor.get_total_pages()
        
        logger.info(f"Processing {total_pages} pages...")
        
        for page_num in range(total_pages):
            try:
                # Check if page is empty
                if extractor.is_empty_page(page_num):
                    continue
                
                # Extract text and layout data
                image, words, boxes = extractor.extract_page_data(page_num)
                
                # Parse invoice data (returns list of shipments)
                shipments_data = parser.parse_invoice(image, words, boxes)
                
                if shipments_data:
                    for shipment in shipments_data:
                        shipment['page_number'] = page_num + 1
                        extracted_data.append(shipment)
                    
                    logger.info(f"Page {page_num + 1}: {len(shipments_data)} shipments extracted")
                
            except Exception as e:
                logger.warning(f"Error processing page {page_num + 1}: {str(e)}")
                continue
        
        extractor.close()
        
        # Save results to CSV
        if extracted_data:
            output_filename = f"extracted_invoices_{unique_id}.csv"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            df = pd.DataFrame(extracted_data)
            
            # Ensure all required columns exist
            required_columns = ['invoice_number', 'account_number', 'invoice_date', 'shipment_date', 'tracking_number', 'receiver_name', 'receiver_address', 'page_number']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # Reorder columns
            df = df[required_columns]
            df.to_csv(output_path, index=False)
            
            logger.info(f"Extraction completed! {len(extracted_data)} shipments found")
            
            return {
                'success': True,
                'message': f'Successfully extracted {len(extracted_data)} shipments from {total_pages} pages',
                'total_pages': total_pages,
                'total_shipments': len(extracted_data),
                'download_id': unique_id,
                'filename': output_filename
            }
        else:
            return {
                'success': False,
                'message': 'No invoice data found in the PDF',
                'total_pages': total_pages,
                'total_shipments': 0
            }
            
    except Exception as e:
        logger.error(f"Error in process_pdf: {str(e)}")
        raise

@app.route('/download/<download_id>')
def download_file(download_id):
    """Download the generated CSV file"""
    try:
        filename = f"extracted_invoices_{download_id}.csv"
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Send file and clean up after sending
        def remove_file(response):
            try:
                os.remove(file_path)
            except Exception:
                pass
            return response
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"invoice_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error in download: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/status')
def status():
    """API endpoint to check server status"""
    return jsonify({
        'status': 'running',
        'message': 'Invoice Extraction Service is operational'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)