import os
import uuid
import logging
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from threading import Thread
from text_extractor import PDFTextExtractor
from invoice_parser import InvoiceParser

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Initialize SocketIO with debugging enabled
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

# Store active sessions
active_sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def emit_progress(session_id, data):
    """Helper function to emit progress with proper error handling"""
    try:
        logger.info(f"EMITTING PROGRESS to session {session_id}: {data}")
        socketio.emit('progress_update', data, room=session_id)
        # Add a small delay to ensure the message is sent
        time.sleep(0.1)
        logger.info(f"Progress emitted successfully to session {session_id}")
    except Exception as e:
        logger.error(f"Failed to emit progress to session {session_id}: {e}")

def emit_completion(session_id, data):
    """Helper function to emit completion with proper error handling"""
    try:
        logger.info(f"EMITTING COMPLETION to session {session_id}: {data}")
        socketio.emit('processing_complete', data, room=session_id)
        time.sleep(0.1)
        logger.info(f"Completion emitted successfully to session {session_id}")
    except Exception as e:
        logger.error(f"Failed to emit completion to session {session_id}: {e}")

def emit_error(session_id, data):
    """Helper function to emit error with proper error handling"""
    try:
        logger.info(f"EMITTING ERROR to session {session_id}: {data}")
        socketio.emit('processing_error', data, room=session_id)
        time.sleep(0.1)
        logger.info(f"Error emitted successfully to session {session_id}")
    except Exception as e:
        logger.error(f"Failed to emit error to session {session_id}: {e}")

def process_invoice_with_progress(pdf_path, output_path, session_id):
    """Process invoice PDF and return extracted data with real-time progress updates"""
    try:
        logger.info(f"=== STARTING PROCESSING for session: {session_id} ===")
        logger.info(f"PDF Path: {pdf_path}")
        logger.info(f"Output Path: {output_path}")
        
        # Check if session is active
        if session_id not in active_sessions:
            logger.error(f"Session {session_id} not found in active sessions")
            return 0, 0
        
        extractor = PDFTextExtractor(pdf_path)
        parser = InvoiceParser()
        extracted_data = []
        total_pages = extractor.get_total_pages()
        
        logger.info(f"Total pages to process: {total_pages}")
        
        # Emit initial progress
        initial_progress = {
            'current_page': 0,
            'total_pages': total_pages,
            'percentage': 0,
            'status': f'Starting processing... Found {total_pages} pages',
            'shipments_found': 0
        }
        emit_progress(session_id, initial_progress)
        
        processed_pages = 0
        
        for page_num in range(total_pages):
            logger.info(f"=== PROCESSING PAGE {page_num + 1} of {total_pages} ===")
            
            # Emit progress for current page start
            progress_data = {
                'current_page': page_num + 1,
                'total_pages': total_pages,
                'percentage': int((page_num / total_pages) * 100),
                'status': f'Processing page {page_num + 1} of {total_pages}...',
                'shipments_found': len(extracted_data)
            }
            emit_progress(session_id, progress_data)
            
            # Add a small delay to make progress visible
            time.sleep(0.0)
            
            if extractor.is_empty_page(page_num):
                logger.info(f"Page {page_num + 1} is empty, skipping")
                processed_pages += 1
                continue
            
            logger.info(f"Extracting data from page {page_num + 1}")
            image, words, boxes = extractor.extract_page_data(page_num)
            
            logger.info(f"Parsing invoice data from page {page_num + 1}")
            shipments_data = parser.parse_invoice(image, words, boxes)
            
            if shipments_data:
                logger.info(f"Found {len(shipments_data)} shipments on page {page_num + 1}")
                for shipment in shipments_data:
                    shipment['page_number'] = page_num + 1
                    extracted_data.append(shipment)
            else:
                logger.info(f"No shipments found on page {page_num + 1}")
            
            processed_pages += 1
            
            # Emit progress update after processing each page
            completed_progress = {
                'current_page': processed_pages,
                'total_pages': total_pages,
                'percentage': int((processed_pages / total_pages) * 100),
                'status': f'Completed page {processed_pages} of {total_pages}',
                'shipments_found': len(extracted_data)
            }
            emit_progress(session_id, completed_progress)
            
            logger.info(f"=== COMPLETED PAGE {page_num + 1}, Total shipments so far: {len(extracted_data)} ===")
        
        extractor.close()
        logger.info(f"=== PROCESSING COMPLETED. Total shipments: {len(extracted_data)} ===")
        
        # Emit processing completion
        final_progress = {
            'current_page': total_pages,
            'total_pages': total_pages,
            'percentage': 100,
            'status': 'Generating CSV file...',
            'shipments_found': len(extracted_data)
        }
        emit_progress(session_id, final_progress)
        
        if extracted_data:
            logger.info("Creating DataFrame and saving CSV")
            df = pd.DataFrame(extracted_data)
            required_columns = ['invoice_number', 'account_number', 'invoice_date', 
                              'shipment_date', 'tracking_number', 'receiver_name', 
                              'receiver_address', 'page_number']
            
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            
            df = df[required_columns]
            df.to_csv(output_path, index=False)
            logger.info(f"CSV saved successfully: {output_path}")
            
            # Emit completion
            completion_data = {
                'success': True,
                'shipment_count': len(extracted_data),
                'page_count': total_pages,
                'message': f'Successfully extracted {len(extracted_data)} shipments from {total_pages} pages'
            }
            emit_completion(session_id, completion_data)
            
            return len(extracted_data), total_pages
        
        # Emit completion with no data found
        no_data_completion = {
            'success': False,
            'shipment_count': 0,
            'page_count': total_pages,
            'message': 'No invoice data found in the PDF'
        }
        emit_completion(session_id, no_data_completion)
        
        return 0, total_pages
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        # Emit error
        error_data = {'error': str(e)}
        emit_error(session_id, error_data)
        raise e

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("=== UPLOAD REQUEST RECEIVED ===")
        
        if 'file' not in request.files:
            logger.error("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            logger.error("File type not allowed")
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Get session ID from request
        session_id = request.form.get('session_id')
        if not session_id:
            logger.error("No session ID provided")
            return jsonify({'error': 'Session ID required'}), 400
        
        logger.info(f"Processing file: {file.filename} for session: {session_id}")
        
        # Generate unique filenames
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        csv_filename = f"{file_id}_extracted_invoices.csv"
        csv_path = os.path.join(app.config['OUTPUT_FOLDER'], csv_filename)
        
        logger.info(f"Saving file to: {pdf_path}")
        
        # Save uploaded file
        file.save(pdf_path)
        
        # Start processing in a separate thread
        def process_file():
            try:
                logger.info(f"Starting background processing for session: {session_id}")
                process_invoice_with_progress(pdf_path, csv_path, session_id)
                # Clean up uploaded PDF after processing
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    logger.info(f"Cleaned up uploaded file: {pdf_path}")
                # Remove session from active sessions
                if session_id in active_sessions:
                    del active_sessions[session_id]
                    logger.info(f"Removed session {session_id} from active sessions")
            except Exception as e:
                logger.error(f"Error in background processing: {e}", exc_info=True)
                # Clean up files on error
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    if os.path.exists(csv_path):
                        os.remove(csv_path)
                except:
                    pass
                # Remove session from active sessions
                if session_id in active_sessions:
                    del active_sessions[session_id]
        
        thread = Thread(target=process_file)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Background processing started for session: {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Processing started',
            'download_filename': csv_filename
        })
            
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        logger.info(f"Serving download: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500

@socketio.on('connect')
def handle_connect():
    logger.info(f'=== CLIENT CONNECTED ===')
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('=== CLIENT DISCONNECTED ===')

@socketio.on('join_session')
def handle_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        active_sessions[session_id] = {'connected_at': time.time()}
        logger.info(f'=== CLIENT JOINED SESSION: {session_id} ===')
        logger.info(f'Active sessions: {list(active_sessions.keys())}')
        emit('session_joined', {'session_id': session_id})
    else:
        logger.error('No session_id provided in join_session')

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("=== STARTING FLASK-SOCKETIO SERVER ===")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

