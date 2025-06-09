from flask import Flask, request, jsonify, Blueprint, send_from_directory, send_file
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
import pandas as pd
import traceback
import time
import zipfile
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create blueprint for API v1
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Configuration
UPLOAD_FOLDER = 'uploads'
CONFIG_FOLDER = 'config'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)
os.makedirs("./Data/Output", exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_v1.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Backend server is running"}), 200


@api_v1.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and configuration - dummy version"""
    try:
        # Check if file part exists in request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
        
        # Get configuration data
        config_data = json.loads(request.form.get('config', '{}'))

        print("\n=== API: /upload ===")
        print(f"Filename: {file.filename}")
        print(f"Configuration: {json.dumps(config_data, indent=2)}")
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Generate a dummy project_id
        project_name = config_data.get('projectName', 'project')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_id = f"{project_name}_{timestamp}"
        
        # Dummy validation data
        
        validation_data = {
            "levels": {
                "L0": {
                    "name": "Approver 1",
                    "description": "Roles: Oceania Requestor"
                },
                "L1": {
                    "name": "Approver 2",
                    "description": "Roles: Oceania ASO TISO, Oceania Compliance Team, Procurement Head, Oceania Procurement Team, Procurement Head (SG)"
                },
                "L2": {
                    "name": "Approver 3",
                    "description": "Roles: Head of Department(OCN) - Cost Center Owner, Oceania Compliance Team, Procurement Head, Procurement Head (SG)"
                },
                "L3": {
                    "name": "Approver 4",
                    "description": "Roles: Head of Department(OCN) - Cost Center Owner, Procurement Head, Procurement Head (SG)"
                },
                "L4": {
                    "name": "Approver 5",
                    "description": "Roles: Head of Department(OCN) - Cost Center Owner"
                }
            },
            "conditions": {
                "condition1": {
                    "type": "riskAssessmentResults",
                    "description": "Risk Assessment Results = APRA CPS230 (Operational Risk Management)"
                },
                "condition2": {
                    "type": "riskAssessmentResults",
                    "description": "Risk Assessment Results = APRA CPS234 (Information Security)"
                },
                "condition3": {
                    "type": "riskAssessmentResults",
                    "description": "Risk Assessment Results = Both"
                },
                "condition4": {
                    "type": "riskAssessmentResults",
                    "description": "Risk Assessment Results = NA"
                }
            },
            "mapping": {
                "condition1": [
                    "L0",
                    "L1",
                    "L2",
                    "L3",
                ],
                "condition2": [
                    "L0",
                    "L1",
                    "L2",
                    "L3",
                ],
                "condition3": [
                    "L0",
                    "L1",
                    "L2",
                    "L3",
                    "L4"
                ],
                "condition4": [
                    "L0",
                    "L1",
                    "L2",
                    "L3",
                ]
            }
        }
        
        return jsonify({
            "message": "File uploaded and rules extracted successfully",
            "validation_data": validation_data,
            "project_id": project_id
        }), 200
        
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


@api_v1.route('/process-validation', methods=['POST'])
def process_validation():
    """Process validation data and generate tree structure - dummy version"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract the required components
        levels = data.get('levels', {})
        conditions = data.get('conditions', {})
        mapping = data.get('mapping', {})
        project_id = data.get('project_id', '')
        
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400
        
        print("\n=== API: /process-validation ===")
        print(f"Project ID: {project_id}")
        print(f"Levels: {json.dumps(levels, indent=2)}")
        print(f"Conditions: {json.dumps(conditions, indent=2)}")
        print(f"Mapping: {json.dumps(mapping, indent=2)}")
        
        # Dummy tree data
        # with open(r"tree_data.json", "r") as file:
        with open(r"mufg_isource_fs_award_tree_data.json", "r") as file:
            data = json.load(file)
        tree_data = data
        
        return jsonify({
            "message": "Validation data processed successfully",
            "tree_data": tree_data,
            "project_id": project_id
        }), 200
        
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


@api_v1.route('/transform', methods=['POST'])
def transform_tree():
    """Transform tree data to generate MCW and WCM files - dummy version"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract tree data and project ID
        tree_data = data.get('tree_data', {})
        project_id = data.get('project_id', '')
        
        if not tree_data:
            return jsonify({"error": "Tree data is missing or empty"}), 400
            
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        print("\n=== API: /transform ===")
        print(f"Project ID: {project_id}")
        print(f"Tree data: {json.dumps(tree_data, indent=2)}")
        
        # Dummy file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "./Data/Output"
        
        # Create dummy Excel file
        dummy_mcw_file_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.xlsx")
        dummy_mcw_json_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.json")
        
        # Create a simple Excel file
        df = pd.DataFrame({
            'Category': ['Category A', 'Category A', 'Category B', 'Category B'],
            'Subcategory': ['Subcategory A1', 'Subcategory A2', 'Subcategory B1', 'Subcategory B2'],
            'Value': [100, 200, 300, 400]
        })
        df.to_excel(dummy_mcw_file_path, index=False)
        
        # Create a simple JSON file
        with open(dummy_mcw_json_path, 'w') as f:
            json.dump(tree_data, f, indent=4)
        
        # Create response with file paths
        response_data = {
            "message": "Tree data transformed successfully",
            "file_paths": {
                "mcw_file": r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_fs_award_mcw.xlsx",
                "wcm_file": r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_fs_award_wcm.xlsx"
            },
            "project_id": project_id
        }
        
        print(f"Sending response: {json.dumps(response_data, indent=2)}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


# @api_v1.route('/download', methods=['GET'])
# def download_file():
#     """Download a file from the server"""
#     try:
#         # Get file path from query parameters
#         file_path = request.args.get('file', '')
#         file_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_fs_award_mcw.xlsx"
        
#         if not file_path:
#             return jsonify({"error": "No file path provided"}), 400

#         print("\n=== API: /download ===")
#         print(f"File path: {file_path}")
#         print(f"File Exists: {os.path.exists(file_path)}")

#         # Ensure the file exists
#         if not os.path.exists(file_path):
#             return jsonify({"error": "File not found"}), 404
 
#         # Get the directory and filename
#         directory = os.path.dirname(file_path)
#         filename = os.path.basename(file_path)
        
#         # Return the file as an attachment
#         return send_file(file_path, as_attachment=True, download_name=filename)
        
#     except Exception as e:
#         # Log the full exception for debugging
#         traceback.print_exc()
#         return jsonify({"error": "Server error", "details": str(e)}), 500

@api_v1.route('/download', methods=['GET'])
def download_file():
    """Download a file from the server"""
    try:
        # Get file path from query parameters
        file_path = request.args.get('file', '')

        if not file_path:
            return jsonify({"error": "No file path provided"}), 400

        print("\n=== API: /download ===")
        print(f"File path: {file_path}")
        print(f"File Exists: {os.path.exists(file_path)}")

        # Ensure the file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Return the file as an attachment
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

@api_v1.route('/download-mufg', methods=['GET'])
def download_mufg_files():
    """Download fixed MUFG files"""
    try:
        file_type = request.args.get('type', 'all')
        
        # Fixed file paths
        mcw_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_fs_award_mcw.xlsx"
        wcm_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\mufg_isource_fs_award_wcm.xlsx"
        zip_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Projects\Workflow\data\Output\MUFG\Final\Zip Files\MUFG_iSource_MCW-WCM.zip"
        
        print("\n=== API: /download-mufg ===")
        print(f"File type: {file_type}")
        
        # Download based on requested type
        if file_type == 'mcw':
            if os.path.exists(mcw_path):
                return send_file(mcw_path, as_attachment=True, download_name=os.path.basename(mcw_path))
            else:
                return jsonify({"error": "MCW file not found"}), 404
                
        elif file_type == 'wcm':
            if os.path.exists(wcm_path):
                return send_file(wcm_path, as_attachment=True, download_name=os.path.basename(wcm_path))
            else:
                return jsonify({"error": "WCM file not found"}), 404
                
        elif file_type == 'zip' or file_type == 'all':
            if os.path.exists(zip_path):
                return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))
            else:
                # If zip not found, create one with the available files
                temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                
                # Create a unique zip filename
                zip_filename = f"MUFG_iSource_MCW-WCM_{int(time.time())}.zip"
                temp_zip_path = os.path.join(temp_dir, zip_filename)
                
                with zipfile.ZipFile(temp_zip_path, 'w') as zipf:
                    if os.path.exists(mcw_path):
                        zipf.write(mcw_path, os.path.basename(mcw_path))
                    if os.path.exists(wcm_path):
                        zipf.write(wcm_path, os.path.basename(wcm_path))
                
                if os.path.exists(temp_zip_path):
                    return send_file(temp_zip_path, as_attachment=True, download_name=zip_filename)
                else:
                    return jsonify({"error": "No files available to download"}), 404
        
        else:
            return jsonify({"error": "Invalid file type specified"}), 400
            
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


@api_v1.route('/download-all', methods=['GET'])
def download_all_files():
    """Download all files as a zip"""
    try:
        # Get file paths from query parameters
        mcw_file = request.args.get('mcw_file', '')
        wcm_file = request.args.get('wcm_file', '')
        
        print("\n=== API: /download-all ===")
        print(f"MCW File: {mcw_file}")
        print(f"WCM File: {wcm_file}")
        
        # Check if at least one file path is provided
        if not mcw_file and not wcm_file:
            return jsonify({"error": "No files specified for download"}), 400
        
        # Create a temporary directory for the zip file
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a unique zip filename
        zip_filename = f"workflow_files_{int(time.time())}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        # Create zip file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add MCW file if provided
            if mcw_file and os.path.exists(mcw_file):
                mcw_basename = os.path.basename(mcw_file)
                zipf.write(mcw_file, mcw_basename)
                print(f"Added {mcw_basename} to zip")
            
            # Add WCM file if provided
            if wcm_file and os.path.exists(wcm_file):
                wcm_basename = os.path.basename(wcm_file)
                zipf.write(wcm_file, wcm_basename)
                print(f"Added {wcm_basename} to zip")
            
        # Return the zip file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on the server.",
        "status": 404
    }), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal Server Error",
        "message": "The server encountered an internal error and was unable to complete your request.",
        "status": 500
    }), 500

# Register blueprint with the app
app.register_blueprint(api_v1)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 