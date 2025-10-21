const BASE_URL = "https://project-du66.onrender.com";
const resultBox = document.getElementById("result");

// 공통 결과 표시 함수
function showResult(title, data) {
  resultBox.textContent = `${title}\n\n${JSON.stringify(data, null, 2)}`;
}

// ✅ 1. 이력서 업로드
document.getElementById("uploadBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  const file = fileInput.files[0];

  if (!file) {
    alert("PDF 파일을 선택해주세요!");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  showResult("업로드 중...", {});

  try {
    const uploadResponse = await fetch(`${BASE_URL}/extract-and-save-resume`, {
      method: "POST",
      body: formData,
    });

    if (!uploadResponse.ok) throw new Error("이력서 업로드 실패");
    const uploadResult = await uploadResponse.json();

    // 업로드 완료 후 전체 목록 조회
    const getResponse = await fetch(`${BASE_URL}/resumes`);
    if (!getResponse.ok) throw new Error("이력서 목록 불러오기 실패");
    const resumes = await getResponse.json();

    showResult("✅ 업로드 완료 + 전체 목록 조회 성공", {
      uploadResult,
      resumes,
    });
  } catch (error) {
    showResult("❌ 에러 발생", { message: error.message });
  }
});

// ✅ 2. 전체 목록 조회
document.getElementById("getAllBtn").addEventListener("click", async () => {
  showResult("전체 목록 불러오는 중...", {});
  try {
    const response = await fetch(`${BASE_URL}/resumes`);
    if (!response.ok) throw new Error("이력서 목록 불러오기 실패");
    const data = await response.json();
    showResult("📄 전체 이력서 목록", data);
  } catch (error) {
    showResult("❌ 에러 발생", { message: error.message });
  }
});

// ✅ 3. 특정 ID로 이력서 조회
document.getElementById("getByIdBtn").addEventListener("click", async () => {
  const id = document.getElementById("resumeIdInput").value.trim();

  if (!id) {
    alert("이력서 ID를 입력해주세요!");
    return;
  }

  showResult(`이력서(${id}) 조회 중...`, {});

  try {
    const response = await fetch(`${BASE_URL}/resumes/${id}`);
    if (!response.ok) throw new Error(`이력서 조회 실패 (status: ${response.status})`);
    const data = await response.json();
    showResult(`📄 이력서 상세 정보 (${id})`, data);
  } catch (error) {
    showResult("❌ 에러 발생", { message: error.message });
  }
});

// ✅ 4. 특정 ID로 이력서 삭제
document.getElementById("deleteBtn").addEventListener("click", async () => {
  const id = document.getElementById("deleteIdInput").value.trim();

  if (!id) {
    alert("삭제할 이력서 ID를 입력해주세요!");
    return;
  }

  if (!confirm(`정말로 이력서(${id})를 삭제하시겠습니까?`)) return;

  showResult(`이력서(${id}) 삭제 중...`, {});

  try {
    const response = await fetch(`${BASE_URL}/resumes/${id}?hard=true`, {
      method: "DELETE",
    });

    if (!response.ok) throw new Error(`이력서 삭제 실패 (status: ${response.status})`);
    const result = await response.json();

    // 삭제 완료 후 전체 목록 갱신
    const getResponse = await fetch(`${BASE_URL}/resumes`);
    const resumes = await getResponse.json();

    showResult(`🗑️ 이력서(${id}) 삭제 완료`, {
      deleteResult: result,
      updatedResumes: resumes,
    });
  } catch (error) {
    showResult("❌ 에러 발생", { message: error.message });
  }
});
