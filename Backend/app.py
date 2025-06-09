from datetime import datetime
from flask import Flask, abort, request, jsonify, Blueprint, send_from_directory, send_file
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
import pandas as pd
import traceback
import time
import xlrd
import zipfile
import configparser

import pandas as pd
from pandas.errors import EmptyDataError
from GenAIApp import GenAIApp
from MetaDataGeneration import ConditionParser
from WorkflowTransformer import WorkflowTransformer
# Import the image_api blueprint
from app_image import image_api
# Import the blueprint creation function
from agent_core.app_agent import create_file_processor_blueprint


STATIC_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'Frontend', 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER)

CORS(app, supports_credentials=True)

# Create blueprint for API v1
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Configuration
UPLOAD_FOLDER = 'uploads'
CONFIG_FOLDER = 'config'
# Base configuration template
WORKFLOW_CONFIG = {
    "prompts": [
        "level_prompt",
        "condition_prompt",
        "condition_level_mapping_prompt",
        "named_tree_prompt",
        "tree_transform_to_mcw_wcm_prompt"
    ],
    "optimize_prompt": False,
    "extract_levels": True,
    "extract_conditions": True,
    "map_conditions_to_levels": True,
    "map_categories": True,
    "transform_category_mapping": True,
    "tree_chunk_size": 1,
    "transfrom_chunk_size": 3
}
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
# Cache for GenAI instances
genai_instances = {}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CONFIG_FILE_NAME = "configuration.ini"  # Define at module level for potential reuse

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize_path(path):
    """Convert Windows path to Unix-style path"""
    return os.path.normpath(path).replace("\\", "/")

def get_genai_instance(project_name, config_path=None):
    """Get or create a GenAI instance for a project"""
    instance_key = f"{project_name}_{config_path}" if config_path else project_name
    if instance_key not in genai_instances:
        genai_instances[instance_key] = GenAIApp(config_path) if config_path else GenAIApp()
    return genai_instances[instance_key]


@api_v1.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Backend server is running"}), 200


@api_v1.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and configuration"""
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
        
        # Validate configuration data
        validation_errors = validate_config(config_data, file.filename)
        if validation_errors:
            return jsonify({"error": "Configuration validation failed", "details": validation_errors}), 400
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the file (read headers, validate structure, etc.)
        file_processing_result = process_file(file_path, config_data)
        if "error" in file_processing_result:
            return jsonify(file_processing_result), 400
        
        # Generate validation data for the next tab
        row_count = file_processing_result.get("row_count", 50)
        validation_data, project_id = generate_validation_data(config_data, file_path, row_count)
        
        return jsonify({
            "message": "File uploaded and rules extracted successfully",
            "validation_data": validation_data,
            "project_id": project_id
        }), 200
        
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


def validate_config(config, file_name):
    """Validate the configuration data"""
    errors = []

    # Required string fields
    required_strings = [
        ('projectName', "Project name is required"),
        ('projectDescription', "Project description is required"),
        ('mcwId', "MCW ID is required"),
        ('mcwTitle', "MCW title is required"),
        ('mcwProcess', "MCW process is required"),
        ('wcmStartConditionId', "WCM start condition ID is required"),
        ('wcmCurrency', "WCM currency is required"),
        ('wcmDocument', "WCM document is required"),
    ]

    for field, error_msg in required_strings:
        if not config.get(field, '').strip():
            errors.append(error_msg)
    
    # Check numeric fields
    header_row = config.get('headerRow', 0)
    if not isinstance(header_row, int) or header_row <= 0:
        errors.append("Header row must be a positive integer")
    
    data_start_row = config.get('dataStartRow', 0)
    if not isinstance(data_start_row, int) or data_start_row <= 0:
        errors.append("Data start row must be a positive integer")
    
    # Check if data start row is greater than header row
    if isinstance(header_row, int) and isinstance(data_start_row, int) and data_start_row <= header_row:
        errors.append("Data start row must be greater than header row")
    
    # File-specific validation
    file_extension = file_name.rsplit('.', 1)[-1].lower()
    if file_extension in ['xlsx', 'xls']:
        if not config.get('selectedSheet', '').strip():
            errors.append("Sheet name is required for Excel files")

    # Boolean field validation
    if 'enableChaining' in config and not isinstance(config['enableChaining'], bool):
        errors.append("enableChaining must be a boolean value")

    # List field validation
    if 'wcmConditionKeys' in config:
        if not isinstance(config['wcmConditionKeys'], list) or not all(isinstance(k, str) and k.strip() for k in config['wcmConditionKeys']):
            errors.append("wcmConditionKeys must be a list of non-empty strings")
    
    return errors


def process_file(file_path, config):
    """Process the uploaded file based on configuration"""
    try:
        file_extension = file_path.rsplit('.', 1)[1].lower()
        
        # Read the file based on its type
        if file_extension in ['xlsx', 'xls']:
            # For Excel files, use the selected sheet
            sheet_name = config.get('selectedSheet', 'Sheet1')
            df = pd.read_excel(
                file_path, 
                sheet_name=sheet_name
            )

            print(sheet_name)
            print(df.head())
        elif file_extension == 'csv':
            # For CSV files, try UTF-8 first.
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8'
                )
            except UnicodeDecodeError:
                print("UTF-8 failed, trying latin1")
                df = pd.read_csv(
                    file_path,
                    encoding='latin1'
                )
                
        # Basic validation of the dataframe
        if df.empty:
            return {"error": "The file contains no data"}
        
        # Check if there are enough columns
        if len(df.columns) < 2:
            return {"error": "The file should have at least 2 columns"}
        
        # Calculate row count
        row_count = len(df)
        
        # Return success with basic file info and row count
        return {"success": True, "row_count": row_count}
    
    except xlrd.biffh.XLRDError as e:
        return {"error": f"Please remove the 'Zycus-Only' tag and try again."}
    except Exception as e:
        return {"error": f"Error processing file: {str(e)}"}

def find_prompt_file(project_name):
    """Find the appropriate prompt file based on project name"""
    prompts_dir = "prompts"
    default_prompt = "./prompts/workflow_prompts.txt"
    
    # Convert project name to lowercase for case-insensitive comparison
    project_name_lower = project_name.lower()
    
    # List all files in the prompts directory
    try:
        prompt_files = os.listdir(prompts_dir)
        
        # Look for files containing the project name
        for file in prompt_files:
            if project_name_lower in file.lower():
                # Return the first matching file
                return os.path.join(prompts_dir, file)
                
    except Exception as e:
        print(f"Error searching for prompt files: {e}")
    
    # Return default prompt file if no match found
    return default_prompt

def generate_validation_data(config, file_path, row_count):
    file_path = normalize_path(file_path)
    project_name = config.get('projectName', '').strip()
    
    # Generate project ID with date and time as timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS
    project_id = f"{project_name}_{timestamp}"

    # This project_id will be passed through all workflow stages to maintain session context
    print(f"Generated project ID: {project_id}")

    # Find the appropriate prompt file based on project name
    prompt_file = find_prompt_file(project_name)
    print(f"Using prompt file: {prompt_file}")

    # Calculate num_rows (file row count + 1, max 120)
    num_rows = min(row_count + 1, 120)
    
    # Log warning if row count exceeds maximum
    if row_count + 1 > 120:
        print(f"WARNING: File has {row_count} rows, exceeding maximum of 120 rows for processing. Using 75 rows.")
    
    # Create workflow config
    workflow_config = {
        **WORKFLOW_CONFIG,
        "prompt_file": prompt_file,
        "file_path": file_path,
        "header_rows": config.get('headerRow', 1),
        "data_start_row": config.get('dataStartRow', 2),
        "chaining": config.get('enableChaining', False),
        "note": config.get('projectDescription', ''),
        "num_rows": int(num_rows),  # Ensure it's an integer
        "sheet_name": config.get('selectedSheet'),
        # New fields
        "mcw_id": config.get('mcwId', ''),
        "mcw_title": config.get('mcwTitle', ''),
        "mcw_process": config.get('mcwProcess', ''),
        "wcm_start_condition_id": config.get('wcmStartConditionId', ''),
        "wcm_currency": config.get('wcmCurrency', ''),
        "wcm_document": config.get('wcmDocument', ''),
        "wcm_condition_keys": config.get('wcmConditionKeys', [])
    }

    # Define project config file path
    project_config_file_path = os.path.join(CONFIG_FOLDER, f"{project_name}_workflow.json")

    # Load existing project workflows or create new file
    try:
        with open(project_config_file_path, 'r') as f:
            workflows = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        workflows = {}

     # Add new workflow config
    workflows[project_id] = workflow_config

     # Save updated workflows to project-specific file
    with open(project_config_file_path, 'w') as f:
        json.dump(workflows, f, indent=4)

    # Initialize GenAI instance and execute validation stages
    genai_instance = get_genai_instance(project_name, project_config_file_path)
    
    # Define mapping of stages to proper keys
    stage_mapping = {
        "extract_levels": "levels",
        "extract_conditions": "conditions",
        "map_conditions_to_levels": "mapping"
    }

    # Run workflows and store results with proper keys
    results = {
        key: genai_instance.run_workflow(project_id, stage=stage)
        for stage, key in stage_mapping.items()
    }

    return results, project_id


@api_v1.route('/process-validation', methods=['POST'])
def process_validation():
    """Process validation data and generate tree structure"""
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
        
        # Extract project name from project_id
        project_name = '_'.join(project_id.split('_')[:-2]).strip()

        # Sort the mapping keys and values
        sorted_mapping = sort_mapping(mapping)

        print("\n=== API: /process-validation ===")
        print(f"Project ID: {project_id}")
        print(f"Levels: {json.dumps(levels, indent=2)}")
        print(f"Conditions: {json.dumps(conditions, indent=2)}")
        print(f"Mapping: {json.dumps(sorted_mapping, indent=2)}")
        
        # Validate the received data
        validation_errors = validate_validation_data(levels, conditions, sorted_mapping)
        if validation_errors:
            return jsonify({"error": "Validation data processing failed", "details": validation_errors}), 400
        
        # Get the project-specific config path
        project_config_file_path = os.path.join(CONFIG_FOLDER, f"{project_name}_workflow.json")
        print()
        print(project_config_file_path)
        # Get or create GenAI instance for the project
        genai_instance = get_genai_instance(project_name, project_config_file_path)

        # Store the current validation data in the GenAI instance results
        genai_instance.results = {
            'levels': levels,
            'conditions': conditions,
            'mappings': sorted_mapping,
            'max_length': max(len(v) for v in sorted_mapping.values()) if sorted_mapping else 0
        }
        
        # Process the validation data to create tree structure using GenAI
        tree_data = genai_instance.run_workflow(project_id, stage="map_categories")
        
        return jsonify({
            "message": "Validation data processed successfully",
            "tree_data": tree_data,
            "project_id": project_id
        }), 200
        
    except Exception as e:
        # Log the full exception for debugging
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

def sort_mapping(mapping):
    """Sort mapping keys and values properly"""
    # Create a new sorted mapping
    sorted_mapping = {}
    
    # Sort the keys
    sorted_keys = sorted(mapping.keys())
    
    # Helper function to sort level IDs (L0, L1, L2, etc.)
    def level_key(level_id):
        # Extract the numeric part from the level ID (e.g., "L10" -> 10)
        if level_id.startswith('L') and level_id[1:].isdigit():
            return int(level_id[1:])
        return level_id  # Fallback for non-standard format
    
    # For each key, sort the values and add to the sorted mapping
    for key in sorted_keys:
        if isinstance(mapping[key], list):
            # Sort the level IDs properly
            sorted_mapping[key] = sorted(mapping[key], key=level_key)
        else:
            sorted_mapping[key] = mapping[key]
    
    return sorted_mapping

def validate_validation_data(levels, conditions, mapping):
    """Validate the validation data received from frontend"""
    errors = []
    
    # Check if levels data is valid
    if not levels or not isinstance(levels, dict):
        errors.append("Levels data is missing or invalid")
    else:
        # Check if each level has required fields
        for level_id, level_data in levels.items():
            if not isinstance(level_data, dict):
                errors.append(f"Level data for {level_id} is not in the correct format")
                continue
                
            if 'name' not in level_data or not level_data.get('name', '').strip():
                errors.append(f"Level {level_id} is missing a name")
                
            if 'description' not in level_data:
                errors.append(f"Level {level_id} is missing a description")
    
    # Check if conditions data is valid
    if not conditions or not isinstance(conditions, dict):
        errors.append("Conditions data is missing or invalid")
    else:
        # Check if each condition has required fields
        for condition_id, condition_data in conditions.items():
            if not isinstance(condition_data, dict):
                errors.append(f"Condition data for {condition_id} is not in the correct format")
                continue
                
            if 'description' not in condition_data or not condition_data.get('description', '').strip():
                errors.append(f"Condition {condition_id} is missing a description")
                
            if 'type' not in condition_data or not condition_data.get('type', '').strip():
                errors.append(f"Condition {condition_id} is missing a type")
    
    # Check if mapping data is valid
    if not mapping or not isinstance(mapping, dict):
        errors.append("Mapping data is missing or invalid")
    else:
        # Check if each mapping references valid conditions and levels
        for condition_id, level_ids in mapping.items():
            if condition_id not in conditions:
                errors.append(f"Mapping references non-existent condition: {condition_id}")
                continue
                
            if not isinstance(level_ids, list):
                errors.append(f"Mapping for condition {condition_id} is not a list")
                continue
                
            for level_id in level_ids:
                if level_id not in levels:
                    errors.append(f"Mapping references non-existent level: {level_id}")
    
    return errors


@api_v1.route('/transform', methods=['POST'])
def transform_tree():
    """Transform tree data to generate MCW and WCM files"""
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

        # Extract project name from project_id
        project_name = '_'.join(project_id.split('_')[:-2]).strip()

        # Validate tree data
        validation_errors = validate_tree_data(tree_data)
        if validation_errors:
            return jsonify({"error": "Tree data validation failed", "details": validation_errors}), 400

        print("\n=== API: /transform ===")
        print(f"Project ID: {project_id}")
        print(f"Tree data: {json.dumps(tree_data, indent=2)}")
        
        # tree_file_path = os.path.join(os.getcwd(), "mufg_isource_fs_publish_tree_data.json")
        # with open(tree_file_path, "w", encoding="utf-8") as f:
        #     json.dump(tree_data, f, ensure_ascii=False, indent=4)
        
        # Get the project-specific config path
        project_config_file_path = os.path.join(CONFIG_FOLDER, f"{project_name}_workflow.json")

        # Example integration inside /transform
        transformer = WorkflowTransformer(project_id, project_config_file_path)
        transformed = transformer.transform_to_condition_rules(tree_data)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join('./Data/Output', project_name)
        os.makedirs(out_dir, exist_ok=True)

        mcw_path = os.path.join(out_dir, f"workflow_mcw_{timestamp}.xlsx")
        wcm_path = os.path.join(out_dir, f"workflow_wcm_{timestamp}.xlsx")
        metadata_path = os.path.join(out_dir, f"workflow_metadata_{timestamp}.xlsx")

        transformer.save_to_mcw_wcm(transformed, mcw_path, wcm_path)
        # Generate MetaData
        condition_parser = ConditionParser(wcm_path)
        condition_parser.run(metadata_path)

        return jsonify({
            "message": "Tree data transformed successfully",
            "file_paths": {
                "mcw_file": mcw_path,
                "wcm_file": wcm_path,
                "metadata_file": metadata_path
            },
            "project_id": project_id
        }), 200
        
        return jsonify({"error": "Server error", "details": "Test"}), 500
        
        # Get or create GenAI instance for the project
        genai_instance = get_genai_instance(project_name, project_config_file_path)
        
        # Store the category mapping in the GenAI instance results
        genai_instance.results['category_mapping'] = tree_data
        
        # Generate MCW and WCM files using GenAI
        transformed_data = genai_instance.run_workflow(project_id, stage="transform")
        
        # Get the file paths from the GenAI timestamp
        timestamp = genai_instance.gemini.timestamp
        output_dir = "./Data/Output"
        mcw_file_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.xlsx")
        mcw_json_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.json")
        
        return jsonify({
            "message": "Tree data transformed successfully",
            "file_paths": {
                "mcw_file": mcw_file_path,
                "mcw_json": mcw_json_path
            },
            "project_id": project_id
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

def validate_tree_data(tree_data):
    """Validate the tree data received from frontend"""
    errors = []
    
    # Check if tree data is empty
    if not tree_data or (isinstance(tree_data, dict) and len(tree_data) == 0):
        errors.append("Tree is empty")
        return errors
    
    return errors


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
        if os.path.exists(file_path):
            print(f"File Size: {os.path.getsize(file_path)} bytes")

        # Ensure the file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
 
        # Get the directory and filename
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Ensure the file is within allowed directories
        upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
        output_folder = os.path.abspath("./Data/Output")
        file_abs_path = os.path.abspath(file_path)
        
        if not (file_abs_path.startswith(upload_folder) or file_abs_path.startswith(output_folder)):
            return jsonify({"error": "Access denied"}), 403
        
        # Return the file as an attachment
        return send_from_directory(directory, filename, as_attachment=True)
        
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
        metadata_file = request.args.get('metadata_file', '')
        
        print("\n=== API: /download-all ===")
        print(f"MCW File: {mcw_file}")
        print(f"WCM File: {wcm_file}")
        print(f"MetaData File: {metadata_file}")
        
        # Check if at least one file path is provided
        if not mcw_file and not wcm_file and not metadata_file:
            return jsonify({"error": "No files specified for download"}), 400
        
        # Create a temporary directory for the zip file
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a unique zip filename
        zip_filename = f"workflow_files_{int(time.time())}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        # Flag to determine if we should clean up the temp file
        clean_temp_file = True
        
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

            # Add MetaData file if provided
            if metadata_file and os.path.exists(metadata_file):
                metadata_basename = os.path.basename(metadata_file)
                zipf.write(metadata_file, metadata_basename)
                print(f"Added {metadata_basename} to zip")
            
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
@api_v1.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on the server.",
        "status": 404
    }), 404

@api_v1.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal Server Error",
        "message": "The server encountered an internal error and was unable to complete your request.",
        "status": 500
    }), 500
    
    
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """
    Serve the React Single Page Application (SPA) and static assets.
   
    This is a universal route handler that manages all non-API requests by:
    1. Serving actual static files when they exist (JS, CSS, images, etc.)
    2. Falling back to index.html for all client-side routes to enable React Router
   
    The function implements the standard SPA hosting pattern where the server
    delegates routing to the client-side JavaScript application, while still
    efficiently serving static assets directly.
   
    Args:
        path (str): The URL path requested by the client. Empty for root URL.
   
    Returns:
        Response: Either the requested static file or index.html for client routing.
                 Returns a 404 for API paths or 500 if index.html is missing.
   
    Notes:
        - API routes (/api/*) are handled by other specific route handlers
        - SPA routes like /dashboard, /mappings are nonexistent on the server but
          will serve index.html, allowing React Router to handle them client-side
    """
    print(f"Serving frontend request for path: {path}")
   
    # Skip API paths (they should be handled by other routes)
    if path.startswith('api/'):
        print(f"API path not found: {path}")
        return abort(404)
   
    # Define paths for static assets and index.html
    static_file_dir = os.path.abspath(app.static_folder)
    index_path = os.path.join(static_file_dir, 'index.html')
   
    try:
        # First, try to serve actual static files if they exist
        requested_file = os.path.join(static_file_dir, path)
        if path and os.path.isfile(requested_file):
            print(f"Serving static file: {path}")
            return send_from_directory(app.static_folder, path)
       
        # For client-side routes, serve index.html if it exists
        if os.path.exists(index_path):
            print(f"Path '{path}' not found, serving index.html for SPA routing")
            return send_from_directory(app.static_folder, 'index.html')
        else:
            # Critical error: index.html is missing
            print(f"Index file not found at {index_path}")
            return jsonify({
                "error": "Frontend not built or not found",
                "details": "The React app's index.html file is missing. Please ensure the frontend is built correctly."
            }), 500
   
    except Exception as e:
        # Catch and log any unexpected errors
        print(f"Error serving frontend request for path '{path}': {str(e)}")
        return jsonify({
            "error": "Server error",
            "details": f"An error occurred while serving the request: {str(e)}"
        }), 500    
    

# --- Workflow Runs and Stats Endpoints (for Dashboard) ---
# This is a placeholder implementation using mock data.
# Replace with actual database queries when persistence is added.

mock_workflow_runs = [
  {
    'id': '1',
    'name': 'Invoice Processing',
    'type': 'excel',
    'status': 'completed',
    'stage': 'download',
    'progress': 100,
    'createdAt': datetime.now().isoformat(), # Use ISO format string
    'updatedAt': datetime.now().isoformat(),
  },
  {
    'id': '2',
    'name': 'Contract Workflow',
    'type': 'excel',
    'status': 'processing',
    'stage': 'validation',
    'progress': 65,
    'createdAt': datetime.now().isoformat(),
    'updatedAt': datetime.now().isoformat(),
  },
  {
    'id': '3',
    'name': 'Purchase Order Scan',
    'type': 'image',
    'status': 'processing',
    'stage': 'extracting',
    'progress': 30,
    'createdAt': datetime.now().isoformat(),
    'updatedAt': datetime.now().isoformat(),
  },
  {
    'id': '4',
    'name': 'Vendor Management Process',
    'type': 'image',
    'status': 'completed',
    'stage': 'download',
    'progress': 100,
    'createdAt': datetime.now().isoformat(),
    'updatedAt': datetime.now().isoformat(),
  },
  {
    'id': '5',
    'name': 'Expense Report Analysis',
    'type': 'excel',
    'status': 'failed',
    'stage': 'validation',
    'progress': 45,
    'createdAt': datetime.now().isoformat(),
    'updatedAt': datetime.now().isoformat(),
  }
]

@api_v1.route('/workflow-runs', methods=['GET'])
def get_workflow_runs():
    """Fetch workflow runs for the dashboard with pagination and filtering."""
    page = request.args.get('page', 1, type=int)
    pageSize = request.args.get('pageSize', 10, type=int)
    workflow_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')

    # Apply filters to mock data
    filtered_runs = mock_workflow_runs
    if workflow_type != 'all':
        filtered_runs = [run for run in filtered_runs if run['type'] == workflow_type]
    if status != 'all':
        filtered_runs = [run for run in filtered_runs if run['status'] == status]

    # Apply pagination
    total_runs = len(filtered_runs)
    start_index = (page - 1) * pageSize
    end_index = start_index + pageSize
    paginated_runs = filtered_runs[start_index:end_index]

    total_pages = (total_runs + pageSize - 1) // pageSize

    return jsonify({
        'status': 'success',
        'data': paginated_runs,
        'total': total_runs,
        'page': page,
        'pageSize': pageSize,
        'totalPages': total_pages
    }), 200

@api_v1.route('/workflow-stats', methods=['GET'])
def get_workflow_stats():
    """Fetch dashboard statistics for workflow runs."""
    completed = len([run for run in mock_workflow_runs if run['status'] == 'completed'])
    processing = len([run for run in mock_workflow_runs if run['status'] == 'processing'])
    failed = len([run for run in mock_workflow_runs if run['status'] == 'failed'])
    total = len(mock_workflow_runs)

    return jsonify({
        'status': 'success',
        'stats': {
            'completed': completed,
            'processing': processing,
            'failed': failed,
            'total': total
        }
    }), 200

# Register blueprint with the app
app.register_blueprint(api_v1)
# Register image_api blueprint
app.register_blueprint(image_api)
# Register file_processor_api blueprint
# app.register_blueprint(file_processor_api)

# Create and register the file_processor_api blueprint
file_processor_api = create_file_processor_blueprint()
app.register_blueprint(file_processor_api)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
