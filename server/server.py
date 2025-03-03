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

# ★ 全オリジン許可（開発・PoC向け）
CORS(app)

# ディレクトリ設定
BASE_DIR = os.path.dirname(__file__)

# ★ ここで、UPLOADS_DIR を設定。なければ作る。
UPLOADS_DIR = os.path.join(BASE_DIR, "upload")
os.makedirs(UPLOADS_DIR, exist_ok=True)

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# JSONファイルのパス
MATERIALS_JSON = os.path.join(BASE_DIR, "materials.json")
UPLOADS_JSON = os.path.join(BASE_DIR, "uploads.json")

# JSONファイルの初期化
if not os.path.exists(MATERIALS_JSON):
    with open(MATERIALS_JSON, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    logger.info(f"Created {MATERIALS_JSON}")

if not os.path.exists(UPLOADS_JSON):
    with open(UPLOADS_JSON, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    logger.info(f"Created {UPLOADS_JSON}")

######################################
# 商品リスト（GET /materials）
######################################
@app.route('/materials', methods=['GET'])
def get_materials():
    logger.info("Fetching materials list")
    try:
        with open(MATERIALS_JSON, 'r', encoding='utf-8') as f:
            materials = json.load(f)
        logger.debug(f"Materials data (unique count): {len(materials)} items - {materials}")
        return jsonify(materials)
    except FileNotFoundError:
        logger.error(f"Materials JSON file not found: {MATERIALS_JSON}")
        return jsonify({"error": "Materials file not found"}), 500
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in materials file: {MATERIALS_JSON}")
        return jsonify({"error": "Invalid materials data"}), 500
    except PermissionError:
        logger.error(f"Permission denied to read materials file: {MATERIALS_JSON}")
        return jsonify({"error": "Permission denied to read materials file"}), 403

######################################
# 商品ファイルダウンロード（GET /materials/<id>?type=image|text）
######################################
@app.route('/materials/<int:id>', methods=['GET'])
def get_material(id):
    logger.info(f"Fetching material with ID: {id}")
    try:
        with open(MATERIALS_JSON, 'r', encoding='utf-8') as f:
            materials = json.load(f)
        for material in materials:
            if material["id"] == id:
                file_type = request.args.get('type', 'image')  # "image" or "text"
                file_path = os.path.join(DATA_DIR, material[file_type])
                logger.debug(f"Looking for file: {file_path}")
                if os.path.exists(file_path):
                    logger.info(f"Sending file: {file_path}")
                    return send_file(file_path)
                logger.warning(f"File not found: {file_path}")
                return jsonify({"error": "File not found"}), 404
        logger.warning(f"Material not found: {id}")
        return jsonify({"error": "Material not found"}), 404
    except Exception as e:
        logger.error(f"Error processing material request: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

######################################
# エビデンスアップロード（POST /uploads）
######################################
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

    # ファイル保存先を upload/ に変更
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evidence_{material_id}_{timestamp}.png"
    file_path = os.path.join(UPLOADS_DIR, filename)  # ★ここでUPLOADS_DIRを使用
    try:
        screenshot.save(file_path)
        logger.info(f"Saved screenshot: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save screenshot: {str(e)}")
        return jsonify({"error": f"Failed to save screenshot: {str(e)}"}), 500

    # QRコードの生成
    qr_filename = f"qr_reward_{material_id}_{timestamp}.png"
    qr_path = os.path.join(BASE_DIR, "qr", qr_filename)
    qr = qrcode.make(url)
    qr.save(qr_path)

    # アップロード情報の記録
    evidence = {
        "id": f"{material_id}_{timestamp}",
        "material_id": material_id,
        "screenshot": filename,
        "qr_path": qr_filename,  # QRコードのファイル名を保存
        "url": url,
        "comment": comment,
        "status": "pending",
        "timestamp": timestamp
    }
    try:
        with open(UPLOADS_JSON, 'r+', encoding='utf-8') as f:
            uploads = json.load(f)
            uploads.append(evidence)
            f.seek(0)
            json.dump(uploads, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to update uploads JSON: {str(e)}")
        return jsonify({"error": f"Failed to register evidence: {str(e)}"}), 500

    logger.info(f"Evidence registered: {evidence['id']}")
    return jsonify({"message": "Evidence uploaded", "evidence_id": evidence["id"]})

######################################
# 審査処理（管理者向け） POST /review/<evidence_id>
######################################
@app.route('/review/<evidence_id>', methods=['POST'])
def review_evidence(evidence_id):
    action = request.json.get('action')  # "approve" or "reject"
    logger.info(f"Reviewing evidence {evidence_id} with action: {action}")
    try:
        with open(UPLOADS_JSON, 'r+', encoding='utf-8') as f:
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
                    json.dump(uploads, f, ensure_ascii=False, indent=2)
                    return jsonify({
                        "message": f"Evidence {action}d",
                        "qr_path": upload.get("qr_path", "")
                    })
            logger.warning(f"Evidence not found: {evidence_id}")
            return jsonify({"error": "Evidence not found"}), 404
    except Exception as e:
        logger.error(f"Error processing review: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

######################################
# QRコード生成
######################################
def generate_qr_code(material_id, timestamp):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Reward for material {material_id} at {timestamp}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_filename = f"qr_reward_{material_id}_{timestamp}.png"
    qr_path = os.path.join(BASE_DIR, "qr", qr_filename)  # qr ディレクトリに保存
    logger.debug(f"Generating QR code at: {qr_path}")
    qr_img.save(qr_path)
    logger.info(f"Generated QR code: {qr_filename}")
    return qr_filename

######################################
# QRコード配信（GET /qr/<qr_filename>）
######################################
@app.route('/qr/<qr_filename>', methods=['GET'])
def get_qr(qr_filename):
    logger.debug(f"Requesting QR code: {qr_filename}")
    qr_path = os.path.join(BASE_DIR, "qr", qr_filename)
    logger.debug(f"Checking QR code file: {qr_path}")
    if os.path.exists(qr_path):
        logger.info(f"Sending QR code: {qr_path}")
        return send_file(qr_path)
    logger.warning(f"QR code not found at: {qr_path}")
    return jsonify({"error": "QR code not found"}), 404

######################################
# エビデンスステータス確認（GET /uploads）
######################################
@app.route('/uploads', methods=['GET'])
def get_uploads():
    logger.info("Fetching uploads list")
    try:
        with open(UPLOADS_JSON, 'r', encoding='utf-8') as f:
            uploads = json.load(f)
        return jsonify(uploads)
    except FileNotFoundError:
        logger.error(f"Uploads JSON file not found: {UPLOADS_JSON}")
        return jsonify({"error": "Uploads file not found"}), 500
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in uploads file: {UPLOADS_JSON}")
        return jsonify({"error": "Invalid uploads data"}), 500
    except PermissionError:
        logger.error(f"Permission denied to read uploads file: {UPLOADS_JSON}")
        return jsonify({"error": "Permission denied to read uploads file"}), 403

######################################
# サーバー状態確認（GET /status）
######################################
@app.route('/status', methods=['GET'])
def get_status():
    try:
        with open(MATERIALS_JSON, 'r', encoding='utf-8') as f:
            materials_count = len(json.load(f))
        with open(UPLOADS_JSON, 'r', encoding='utf-8') as f:
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
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

######################################
# メイン実行
######################################
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
    # すべてのインターフェイスでリッスンする
    app.run(host='0.0.0.0', port=8080, debug=True)
