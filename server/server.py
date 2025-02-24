from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os
import json
import qrcode
from datetime import datetime
import logging
import argparse

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ディレクトリ設定
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# JSONファイルのパス
MATERIALS_JSON = os.path.join(BASE_DIR, "materials.json")
UPLOADS_JSON = os.path.join(BASE_DIR, "uploads.json")

# JSONファイルの初期化
if not os.path.exists(MATERIALS_JSON):
    with open(MATERIALS_JSON, 'w') as f:
        json.dump([], f)
    logger.info(f"Created {MATERIALS_JSON}")
if not os.path.exists(UPLOADS_JSON):
    with open(UPLOADS_JSON, 'w') as f:
        json.dump([], f)
    logger.info(f"Created {UPLOADS_JSON}")

# 商品リスト取得
@app.route('/materials', methods=['GET'])
def get_materials():
    logger.info("Fetching materials list")
    with open(MATERIALS_JSON, 'r') as f:
        materials = json.load(f)
    return jsonify(materials)

# 商品ファイルダウンロード
@app.route('/materials/<int:id>', methods=['GET'])
def get_material(id):
    logger.info(f"Fetching material with ID: {id}")
    with open(MATERIALS_JSON, 'r') as f:
        materials = json.load(f)
    for material in materials:
        if material["id"] == id:
            file_type = request.args.get('type', 'image')
            file_path = os.path.join(DATA_DIR, material[file_type])
            if os.path.exists(file_path):
                logger.info(f"Sending file: {file_path}")
                return send_file(file_path)
            logger.warning(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404
    logger.warning(f"Material not found: {id}")
    return jsonify({"error": "Material not found"}), 404

# エビデンスアップロード
@app.route('/uploads', methods=['POST'])
def upload_evidence():
    if 'screenshot' not in request.files:
        logger.error("No screenshot provided in request")
        return jsonify({"error": "No screenshot provided"}), 400
    
    screenshot = request.files['screenshot']
    url = request.form.get('url', '')
    comment = request.form.get('comment', '')
    material_id = int(request.form.get('material_id', 0))
    
    # バリデーション
    if not url.startswith('http') or screenshot.mimetype not in ['image/png', 'image/jpeg']:
        logger.error(f"Invalid input: URL={url}, MIME={screenshot.mimetype}")
        return jsonify({"error": "Invalid URL or file format"}), 400
    
    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evidence_{material_id}_{timestamp}.png"
    screenshot.save(os.path.join(DATA_DIR, filename))
    logger.info(f"Saved screenshot: {filename}")
    
    # エビデンス登録
    evidence = {
        "id": f"{material_id}_{timestamp}",
        "material_id": material_id,
        "screenshot": filename,
        "url": url,
        "comment": comment,
        "status": "pending",
        "timestamp": timestamp
    }
    with open(UPLOADS_JSON, 'r+') as f:
        uploads = json.load(f)
        uploads.append(evidence)
        f.seek(0)
        json.dump(uploads, f, indent=2)
    logger.info(f"Evidence registered: {evidence['id']}")
    
    return jsonify({"message": "Evidence uploaded", "evidence_id": evidence["id"]})

# 審査処理（管理者向け）
@app.route('/review/<evidence_id>', methods=['POST'])
def review_evidence(evidence_id):
    action = request.json.get('action')  # "approve" or "reject"
    logger.info(f"Reviewing evidence {evidence_id} with action: {action}")
    with open(UPLOADS_JSON, 'r+') as f:
        uploads = json.load(f)
        for upload in uploads:
            if upload["id"] == evidence_id:
                if action == "approve":
                    upload["status"] = "approved"
                    qr_filename = generate_qr_code(upload["material_id"], upload["timestamp"])
                    upload["qr_path"] = f"/qr/{evidence_id}"
                    logger.info(f"Approved evidence {evidence_id}, QR generated: {qr_filename}")
                elif action == "reject":
                    upload["status"] = "rejected"
                    logger.info(f"Rejected evidence {evidence_id}")
                f.seek(0)
                json.dump(uploads, f, indent=2)
                return jsonify({"message": f"Evidence {action}d", "qr_path": upload.get("qr_path", "")})
    logger.warning(f"Evidence not found: {evidence_id}")
    return jsonify({"error": "Evidence not found"}), 404

# QRコード生成
def generate_qr_code(material_id, timestamp):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Reward for material {material_id} at {timestamp}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_filename = f"qr_reward_{material_id}_{timestamp}.png"
    qr_img.save(os.path.join(DATA_DIR, qr_filename))
    logger.info(f"Generated QR code: {qr_filename}")
    return qr_filename

# QRコード配信
@app.route('/qr/<evidence_id>', methods=['GET'])
def get_qr(evidence_id):
    qr_path = os.path.join(DATA_DIR, f"qr_reward_{evidence_id.split('_')[0]}_{evidence_id.split('_')[1]}.png")
    if os.path.exists(qr_path):
        logger.info(f"Sending QR code: {qr_path}")
        return send_file(qr_path)
    logger.warning(f"QR code not found: {qr_path}")
    return jsonify({"error": "QR code not found"}), 404

# エビデンスステータス確認
@app.route('/uploads', methods=['GET'])
def get_uploads():
    logger.info("Fetching uploads list")
    with open(UPLOADS_JSON, 'r') as f:
        uploads = json.load(f)
    return jsonify(uploads)

# サーバー状態確認
@app.route('/status', methods=['GET'])
def get_status():
    with open(MATERIALS_JSON, 'r') as f:
        materials_count = len(json.load(f))
    with open(UPLOADS_JSON, 'r') as f:
        uploads = json.load(f)
        uploads_count = len(uploads)
        pending_count = len([u for u in uploads if u["status"] == "pending"])
        approved_count = len([u for u in uploads if u["status"] == "approved"])
    status = {
        "server": "running",
        "materials_count": materials_count,
        "uploads_count": uploads_count,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "timestamp": datetime.now().isoformat()
    }
    logger.info("Server status requested")
    return jsonify(status)

# コマンドライン引数処理
def parse_args():
    parser = argparse.ArgumentParser(description="Store Agent Promotion System Server")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose logging")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    logger.info("Starting server on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)