from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)  # CORSを有効化
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MATERIALS_FILE = os.path.join(BASE_DIR, 'materials.json')

# materials.jsonの読み込み
def load_materials():
    if os.path.exists(MATERIALS_FILE):
        with open(MATERIALS_FILE, 'r') as f:
            return json.load(f)
    return []

# materials.jsonの保存
def save_materials(materials):
    with open(MATERIALS_FILE, 'w') as f:
        json.dump(materials, f, indent=2)

materials = load_materials()

@app.route('/')
def index():
    return "Welcome to the Materials API"

@app.route('/materials', methods=['GET'])
def get_materials():
    return jsonify(materials)

@app.route('/materials/<int:material_id>', methods=['GET'])
def get_material(material_id):
    material = next((m for m in materials if m['id'] == material_id), None)
    if material:
        return send_from_directory(DATA_DIR, os.path.basename(material['path']))
    return jsonify({'error': 'Material not found'}), 404

@app.route('/materials', methods=['POST'])
def upload_material():
    file = request.files['file']
    material_type = request.form['type']
    material_id = len(materials) + 1
    file_path = os.path.join(DATA_DIR, file.filename)
    file.save(file_path)
    new_material = {
        'id': material_id,
        'name': file.filename,
        'type': material_type,
        'path': file_path
    }
    materials.append(new_material)
    save_materials(materials)
    return jsonify(new_material), 201

if __name__ == '__main__':
    app.run(port=8080, debug=True)