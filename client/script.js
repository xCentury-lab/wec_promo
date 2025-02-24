const serverUrl = 'http://localhost:8080'; // サーバーのURLを設定

// Function to fetch and display material list
async function fetchMaterials() {
  try {
    const response = await fetch(`${serverUrl}/materials`);
    const data = await response.json();
    const listItems = document.getElementById('material-list-items');
    listItems.innerHTML = '';
    data.forEach(material => {
      const li = document.createElement('li');
      li.innerHTML = `${material.name} (<strong>${material.type}</strong>) `;
      const editButton = document.createElement('button');
      editButton.textContent = 'Edit';
      editButton.addEventListener('click', () => loadMaterialForEditing(material.id, material.type));
      li.appendChild(editButton);
      listItems.appendChild(li);
    });
  } catch (error) {
    console.error('Error fetching materials:', error);
  }
}

// Function to load material for editing
async function loadMaterialForEditing(id, type) {
  const editorContent = document.getElementById('editor-content');
  editorContent.innerHTML = '';
  const response = await fetch(`${serverUrl}/materials/${id}`);
  const blob = await response.blob();
  if (type === 'image') {
    const imageUrl = URL.createObjectURL(blob);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = function() {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
      // Add text input for editing
      const textInput = document.createElement('input');
      textInput.type = 'text';
      textInput.placeholder = 'Enter text to add';
      const addTextButton = document.createElement('button');
      addTextButton.textContent = 'Add Text';
      addTextButton.addEventListener('click', () => {
        const text = textInput.value;
        ctx.fillStyle = 'black';
        ctx.font = '20px Arial';
        ctx.fillText(text, 10, 30);
      });
      editorContent.appendChild(canvas);
      editorContent.appendChild(textInput);
      editorContent.appendChild(addTextButton);
    };
    img.src = imageUrl;
  } else if (type === 'text') {
    const text = await blob.text();
    const textArea = document.createElement('textarea');
    textArea.value = text;
    editorContent.appendChild(textArea);
  }
  document.getElementById('material-list').style.display = 'none';
  document.getElementById('editor').style.display = 'block';
}

// Function to download edited material
document.getElementById('download-button').addEventListener('click', () => {
  const editorContent = document.getElementById('editor-content');
  if (editorContent.firstChild.tagName === 'CANVAS') {
    const canvas = editorContent.firstChild;
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'edited_image.jpg';
      a.click();
    }, 'image/jpeg');
  } else if (editorContent.firstChild.tagName === 'TEXTAREA') {
    const text = editorContent.firstChild.value;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'edited_text.txt';
    a.click();
  }
});

// Function to upload new image
document.getElementById('image-upload-button').addEventListener('click', async () => {
  const fileInput = document.getElementById('image-upload-input');
  if (fileInput.files.length) {
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    form.append('type', 'image');
    try {
      await fetch(`${serverUrl}/materials`, {
        method: 'POST',
        body: form
      });
      fetchMaterials();
    } catch (error) {
      console.error('Error uploading image:', error);
    }
  }
});

// Function to upload new text
document.getElementById('text-upload-button').addEventListener('click', async () => {
  const textInput = document.getElementById('text-upload-input');
  const text = textInput.value;
  if (text) {
    const form = new FormData();
    const blob = new Blob([text], { type: 'text/plain' });
    form.append('file', blob, 'uploaded_text.txt');
    form.append('type', 'text');
    try {
      await fetch(`${serverUrl}/materials`, {
        method: 'POST',
        body: form
      });
      fetchMaterials();
    } catch (error) {
      console.error('Error uploading text:', error);
    }
  }
});

// Function to show uploader
document.getElementById('upload-button').addEventListener('click', () => {
  document.getElementById('material-list').style.display = 'none';
  document.getElementById('uploader').style.display = 'block';
});

// Function to go back to material list from editor or uploader
function backToMaterialList() {
  document.getElementById('editor').style.display = 'none';
  document.getElementById('uploader').style.display = 'none';
  document.getElementById('material-list').style.display = 'block';
}

// Add back button to editor and uploader
document.getElementById('editor').innerHTML += '<button id="back-button-editor">Back</button>';
document.getElementById('uploader').innerHTML += '<button id="back-button-uploader">Back</button>';

document.getElementById('back-button-editor').addEventListener('click', backToMaterialList);
document.getElementById('back-button-uploader').addEventListener('click', backToMaterialList);

// Initial fetch of materials
document.addEventListener('DOMContentLoaded', () => {
  fetchMaterials(); // 素材リストを取得して表示
});