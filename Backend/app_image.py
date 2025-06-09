from flask import Blueprint, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import traceback
from werkzeug.utils import secure_filename
from datetime import datetime
from GenerateMCW import GenerateMCW
from GenerateMetadata import GenerateMetadata
from GenerateWCM import GenerateWCM
from Preprocessing import Preprocessing
from utility import get_logger

logger = get_logger()

# Create blueprint for image API
image_api = Blueprint('image_api', __name__, url_prefix='/api/v1/image')

# Configure Blueprint to handle exceptions
@image_api.errorhandler(Exception)
def handle_exception(e):
    """Log unhandled exceptions and return appropriate response"""
    # Get the full traceback
    tb = traceback.format_exc()
    # Log the full exception details
    logger.error(f"Unhandled exception: {str(e)}\n{tb}")
    # Return JSON response for API consistency
    return jsonify({'error': str(e)}), 500

@image_api.route('/health', methods=['GET', 'HEAD'])
def health_check():
    logger.info("Image workflow health check received.")
    return jsonify({'status': 'healthy', 'service': 'image-workflow'}), 200

@image_api.route('/upload', methods=['POST'])
def upload_file():
    logger.info("Image upload request received")
    
    # Read configuration from configuration.ini
    config_dict = Preprocessing.read_config()
    UPLOAD_FOLDER = config_dict.get('UPLOAD_FOLDER', 'uploads')
    OUTPUT_FOLDER = config_dict.get('OUTPUT_FOLDER', 'Output')
    
    if 'UPLOAD_FOLDER' not in config_dict:
        config_dict['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    if 'OUTPUT_FOLDER' not in config_dict:
        config_dict['OUTPUT_FOLDER'] = OUTPUT_FOLDER

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.error("No file selected for uploading")
        return jsonify({'error': 'No file selected for uploading'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        logger.info(f"Image filename :: {filename}")
        file_path = os.path.join(config_dict['UPLOAD_FOLDER'], filename)
        logger.info(f"Saving uploaded file: {filename} to {file_path}")
        file.save(file_path)
        
        # Store the filename in config_dict for later use
        config_dict['IMAGE_NAME'] = filename
        logger.info(f"Stored current filename in config: {filename}")
        
        # Generate expected output file path for later use
        output_file = os.path.join(
            config_dict['OUTPUT_FOLDER'], 
            os.path.splitext(filename)[0] + "_gpt_op.json"
        )
        
        logger.info(f"File {filename} uploaded successfully")
        return jsonify({
            'success': True,
            'filename': filename,
            'outputFile': os.path.splitext(filename)[0] + "_gpt_op.json",
            'imageUrl': f'/image/files/{filename}'
        })

@image_api.route('/current-file', methods=['GET'])
def get_current_file():
    """Return the current filename stored in config_dict"""
    
    config_dict = Preprocessing.read_config()
    current_file = config_dict.get('IMAGE_NAME', None)
    
    if current_file:
        logger.info(f"Current file request: returning {current_file}")
        
        # Construct the expected output file path
        output_file = os.path.splitext(current_file)[0] + "_gpt_op.json"
        output_path = os.path.join(config_dict['OUTPUT_FOLDER'], output_file)
        
        # Check if the output file actually exists
        file_exists = os.path.exists(output_path)
        logger.info(f"Output file {output_file} exists: {file_exists}")
        
        return jsonify({
            'filename': current_file,
            'outputFile': output_file,
            'outputExists': file_exists,
            'outputPath': output_path,
            'imageUrl': f'/image/files/{current_file}'
        })
    else:
        # List any images in the upload folder as a hint
        upload_images = [f for f in os.listdir(config_dict['UPLOAD_FOLDER']) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        logger.info(f"Current file request: no file set. Available images: {upload_images}")
        
        if upload_images:
            # Suggest the first available image
            suggestion = upload_images[0]
            return jsonify({
                'error': 'No current file set in configuration',
                'available_images': upload_images,
                'suggestion': suggestion
            }), 404
        else:
            return jsonify({'error': 'No current file set and no images available'}), 404

@image_api.route('/process', methods=['POST'])
def process_image():
    logger.info("Process image request received")
    
    # Get filename from request
    data = request.get_json()
    if not data or 'filename' not in data:
        logger.error("No filename provided in the request")
        return jsonify({'error': 'No filename provided in the request'}), 400
    
    filename = data['filename']
    logger.info(f"Processing request for image: {filename}")
    
    config_dict = Preprocessing.read_config()
    # Check if file exists
    file_path = os.path.join(config_dict['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        logger.error(f"Image file not found: {file_path}")
        return jsonify({'error': 'Image file not found'}), 404
    
    try:
        # Update config to use the uploaded file
        config_dict['IMAGE_NAME'] = filename
        
        logger.info(f"Starting preprocessing for {filename}")
        # Process the image
        Preprocessing.main()
        
        # Get the output file path
        output_file = os.path.join(
            config_dict['OUTPUT_FOLDER'], 
            os.path.splitext(filename)[0] + "_gpt_op.json"
        )
        
        # Check if output file exists
        if not os.path.exists(output_file):
            logger.error(f"Processing failed, no output file generated for {filename}")
            return jsonify({'error': 'Processing failed, no output file generated'}), 500
        
        logger.info(f"File {filename} processed successfully")
        return jsonify({
            'success': True,
            'filename': filename,
            'outputFile': os.path.splitext(filename)[0] + "_gpt_op.json",
            'imageUrl': f'/image/files/{filename}',
            'data': {'processed': True, 'timestamp': datetime.now().isoformat()}
        })
    
    except Exception as e:
        logger.error(f"Error processing file {filename}: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@image_api.route('/files/<filename>', methods=['GET'])
def get_image(filename):
    """Return the uploaded image file"""
    config_dict = Preprocessing.read_config()
    logger.info(f"Image request received for: {filename}")
    return send_from_directory(config_dict['UPLOAD_FOLDER'], filename)

@image_api.route('/files/<filename>', methods=['DELETE'])
def delete_image(filename):
    """Delete an uploaded image file"""
    config_dict = Preprocessing.read_config()
    logger.info(f"Delete request received for image: {filename}")
    
    file_path = os.path.join(config_dict['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        logger.info(f"Image file not found for deletion: {file_path}, skipping")
        return jsonify({'success': True, 'message': f'Image {filename} already deleted or does not exist'})
    
    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted image: {filename}")
        return jsonify({'success': True, 'message': f'Image {filename} deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting image {filename}: {str(e)}")
        return jsonify({'error': f'Error deleting image: {str(e)}'}), 500

@image_api.route('/workflows/<filename>', methods=['GET'])
def get_workflow(filename):
    logger.info(f"Workflow data request received for: {filename}")
    try:
        config_dict = Preprocessing.read_config()
        
        # If filename is just the image name, convert it to expected output format
        if not filename.endswith('.json'):
            filename = os.path.splitext(filename)[0] + "_gpt_op.json"
        
        file_path = os.path.join(config_dict['OUTPUT_FOLDER'], filename)
        
        # Log the full file path being accessed
        logger.info(f"Attempting to access JSON file at: {file_path}")
        
        # Debug: List files in the output directory
        output_files = [f for f in os.listdir(config_dict['OUTPUT_FOLDER']) if f.endswith('.json')]
        logger.info(f"Available JSON files in {config_dict['OUTPUT_FOLDER']}: {', '.join(output_files)}")
        
        if not os.path.exists(file_path):
            logger.error(f"Workflow file not found: {file_path}")
            # Return helpful error with list of available files
            return jsonify({
                'error': f'File {filename} not found',
                'available_files': output_files,
                'output_folder': config_dict['OUTPUT_FOLDER']
            }), 404
        
        # Log file size and modification time
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size / 1024  # Size in KB
        mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"JSON file found: {filename}, Size: {file_size:.2f} KB, Last modified: {mod_time}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Successfully read and parsed JSON data from {filename}")
            return jsonify(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in file {filename}: {str(e)}")
            return jsonify({'error': f'File is not valid JSON: {str(e)}'}), 400
        
    except Exception as e:
        logger.error(f"Error reading workflow file {filename}: {str(e)}")
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

@image_api.route('/outputs', methods=['GET'])
def list_outputs():
    logger.info("List outputs request received")
    try:
        config_dict = Preprocessing.read_config()
        files = [f for f in os.listdir(config_dict['OUTPUT_FOLDER']) if f.endswith('_gpt_op.json')]
        logger.info(f"Found {len(files)} output files")
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"Error listing output files: {str(e)}")
        return jsonify({'error': f'Error listing files: {str(e)}'}), 500

@image_api.route('/workflows/backup', methods=['POST'])
def backup_workflow():
    logger.info("Backup workflow request received")
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            logger.error("No filename provided in the request")
            return jsonify({'error': 'No filename provided in the request'}), 400
        
        config_dict = Preprocessing.read_config()
        original_file = os.path.join(config_dict['OUTPUT_FOLDER'], data['filename'])
        backup_file = os.path.join(config_dict['OUTPUT_FOLDER'], 
                                 os.path.splitext(data['filename'])[0].replace('_gpt_op', '') + '_gpt_op_og.json')
        
        # Check if backup already exists
        if os.path.exists(backup_file):
            logger.info(f"Backup file already exists: {backup_file}")
            return jsonify({
                'success': True,
                'message': 'Backup already exists',
                'backupFile': os.path.basename(backup_file)
            })
        
        # Check if original file exists
        if not os.path.exists(original_file):
            logger.error(f"Original file not found: {original_file}")
            return jsonify({'error': 'Original file not found'}), 404
        
        # Create backup
        import shutil
        shutil.copy2(original_file, backup_file)
        logger.info(f"Created backup file: {backup_file}")
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'backupFile': os.path.basename(backup_file)
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': f'Error creating backup: {str(e)}'}), 500

@image_api.route('/generate-files', methods=['POST'])
def generate_files():
    logger.info("Generate files request received")
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'options' not in data:
            logger.error("Missing filename or options in generate files request")
            return jsonify({'error': 'Missing filename or options'}), 400

        filename = data['filename']
        options = data['options'] # { mcw: boolean, wcm: boolean, metadata: boolean }
        logger.info(f"Generating files for {filename} with options: {options}")

        config_dict = Preprocessing.read_config()
        client = Preprocessing.configure_client()

        # Construct path to the processed JSON file
        processed_json_filename = os.path.splitext(filename)[0] + "_gpt_op.json"
        processed_json_path = os.path.join(config_dict['OUTPUT_FOLDER'], processed_json_filename)

        if not os.path.exists(processed_json_path):
            logger.error(f"Processed JSON file not found: {processed_json_path}")
            return jsonify({'error': f'Processed JSON file not found: {processed_json_filename}'}), 404

        # Read the processed JSON file
        with open(processed_json_path, 'r', encoding='utf-8') as f:
            parsed_json_list = json.load(f)
        logger.info(f"Successfully loaded processed JSON from {processed_json_filename}")

        generated_files = {}

        if options.get('mcw'):
            logger.info("Generating MCW file")
            # Assuming executeMCW writes to a predictable location based on config and filename
            # We might need to update GenerateMCW to return the output filename if it's not standard
            GenerateMCW.executeMCW(client, config_dict, parsed_json_list)
            generated_files['mcw_file'] = os.path.splitext(filename)[0] + "_MCW.xlsx"
            logger.info(f"MCW file generated: {generated_files['mcw_file']}")

        if options.get('wcm'):
            logger.info("Generating WCM file")
            # Assuming executeWCM writes to a predictable location
            GenerateWCM.executeWCM(client, config_dict, parsed_json_list)
            generated_files['wcm_file'] = os.path.splitext(filename)[0] + "_WCM.xlsx"
            logger.info(f"WCM file generated: {generated_files['wcm_file']}")

        if options.get('metadata'):
            logger.info("Generating Metadata file")
            # Assuming executeMetadata writes to a predictable location
            GenerateMetadata.executeMetadata(client, config_dict, parsed_json_list)
            generated_files['metadata_file'] = os.path.splitext(filename)[0] + "_Metadata.xlsx"
            logger.info(f"Metadata file generated: {generated_files['metadata_file']}")

        if not generated_files:
             return jsonify({'error': 'No output formats selected or generated'}), 400

        return jsonify({'success': True, 'generated_files': generated_files})

    except FileNotFoundError as e:
        logger.error(f"File not found during generation: {str(e)}")
        return jsonify({'error': f'Required file not found: {str(e)}'}), 404
    except Exception as e:
        logger.error(f"Error during file generation: {str(e)}")
        # Log the full traceback for better debugging
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error during generation: {str(e)}'}), 500

@image_api.route('/download-generated-files', methods=['GET'])
def download_generated_files():
    logger.info("Download generated files request received")
    try:
        file_paths = {
            'mcw_file': request.args.get('mcw_file'),
            'wcm_file': request.args.get('wcm_file'),
            'metadata_file': request.args.get('metadata_file')
        }
        
        # Filter out None values and get actual file names
        files_to_zip = {key: value for key, value in file_paths.items() if value}
        
        if not files_to_zip:
            return jsonify({'error': 'No file paths provided for download'}), 400

        config_dict = Preprocessing.read_config()
        output_folder = config_dict['OUTPUT_FOLDER']
        
        # List of full paths for files to add to zip
        full_file_paths = []
        for key, filename in files_to_zip.items():
            file_path = os.path.join(output_folder, filename)
            if os.path.exists(file_path):
                full_file_paths.append((file_path, filename)) # Store as (full_path, filename_in_zip)
            else:
                logger.warning(f"File not found for zipping: {file_path}")
                # Optionally, you could return a 404 or just skip this file

        if not full_file_paths:
             return jsonify({'error': 'None of the requested files were found'}), 404

        # Create a temporary zip file
        temp_zip_path = os.path.join(output_folder, f'workflow_outputs_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip')
        
        import zipfile
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for full_path, filename_in_zip in full_file_paths:
                zipf.write(full_path, arcname=filename_in_zip) # Use arcname to keep just the filename
        logger.info(f"Created temporary zip file: {temp_zip_path}")

        # Send the zip file
        from flask import send_file
        response = send_file(temp_zip_path, as_attachment=True, download_name=os.path.basename(temp_zip_path))

        # Clean up the temporary zip file after sending
        # This requires Flask's after_request or similar, but for simplicity, a small delay might work in some cases.
        # A more robust solution involves Flask's send_file with a custom wrapper or using a background thread.
        # For now, let's just return the response. Manual cleanup might be needed in some environments.
        # os.remove(temp_zip_path) # Don't do this here, file is still being read
        
        return response

    except Exception as e:
        logger.error(f"Error during file download/zipping: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error during download: {str(e)}'}), 500
