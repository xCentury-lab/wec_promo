// ★サーバーURLを実際のIP:ポートに合わせる
const serverUrl = 'http://192.168.11.33:8080'; 
// 例: const serverUrl = 'http://192.168.0.10:8080';

/*----------------------------------------------
 * 1. 商品リストを取得し、materials.html で表示
 *---------------------------------------------*/
async function fetchMaterials() {
  try {
    const response = await fetch(`${serverUrl}/materials`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    const listItems = document.getElementById('material-list-items');
    if (listItems) {
      listItems.innerHTML = ''; // 既存の内容をクリア

      for (const material of data) {
        const div = document.createElement('div');
        div.className = 'material-card';

        // テキストファイルの内容を取得
        const textContent = await fetchMaterialText(material.id);

        div.innerHTML = `
          <span>${material.name} (${material.category})</span>
          <div class="content">
            <img src="${serverUrl}/materials/${material.id}?type=image" alt="${material.name}" onerror="this.style.display='none';">
            <p>${textContent}</p>
          </div>
        `;
        listItems.appendChild(div);
      }
    }
  } catch (error) {
    console.error('Error fetching materials:', error);
    const resultDiv = document.getElementById('result') || document.createElement('div');
    resultDiv.classList.add('error');
    resultDiv.innerText = `商品リストの取得に失敗しました: ${error.message}`;
    document.body.appendChild(resultDiv);
  }
}

/*----------------------------------------------
 * 2. 指定IDのテキストファイルを取得
 *---------------------------------------------*/
async function fetchMaterialText(id) {
  try {
    const response = await fetch(`${serverUrl}/materials/${id}?type=text`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.text();
  } catch (error) {
    console.error('Error fetching material text:', error);
    return 'テキストの取得に失敗しました。';
  }
}

/*----------------------------------------------
 * 3. 全エビデンスアップロード情報を取得
 *---------------------------------------------*/
async function fetchUploads() {
  try {
    const response = await fetch(`${serverUrl}/uploads`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching uploads:', error);
    return [];
  }
}

/*----------------------------------------------
 * 4. 全エビデンスを一覧表示し、ステータスごとに色分け
 *---------------------------------------------*/
async function displayAllUploads() {
  try {
    const uploads = await fetchUploads();
    const container = document.getElementById('approval-list');
    if (!container) {
      console.warn('No element with ID "approval-list" found in the HTML.');
      return;
    }

    container.innerHTML = '';

    if (uploads.length === 0) {
      container.innerHTML = '<p>まだアップロードはありません。</p>';
      return;
    }

    // すべてのアップロードをカード形式で表示
    for (const upload of uploads) {
      const card = document.createElement('div');
      card.className = 'upload-card';

      // ステータスごとに色分けするclass名
      const statusClass = getStatusClass(upload.status);

      card.innerHTML = `
        <div class="${statusClass}">${upload.status}</div>
        <span><strong>ID:</strong> ${upload.id}</span>
        <span><strong>Material ID:</strong> ${upload.material_id}</span>
        <span><strong>URL:</strong> ${upload.url}</span>
        <span><strong>Comment:</strong> ${upload.comment}</span>
        <span><strong>Timestamp:</strong> ${upload.timestamp}</span>
      `;
      container.appendChild(card);
    }
  } catch (error) {
    console.error('Error displaying all uploads:', error);
    const container = document.getElementById('approval-list');
    if (container) {
      container.innerHTML = `<p class="error">アップロード一覧の取得に失敗しました: ${error.message}</p>`;
    }
  }
}

/*----------------------------------------------
 * ステータスに応じたクラス名を返す
 *---------------------------------------------*/
function getStatusClass(status) {
  switch (status) {
    case 'approved':
      return 'status-badge status-approved';
    case 'rejected':
      return 'status-badge status-rejected';
    default:
      // pendingなど
      return 'status-badge status-pending';
  }
}
