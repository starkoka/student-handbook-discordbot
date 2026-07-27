import fitz
import re
import json
from pathlib import Path

student_handbook_path = "student-handbook.pdf"
chunk_size = 1000  # チャンクの最大文字数
chunk_output_path = "RAG/data/student_handbook_chunks.json"

# PDFファイルを開き、ページ番号とテキストを抽出する
student_handbook_pages = []
try:
    doc = fitz.open(student_handbook_path)
    for pdf_page_number in range(len(doc)):
        page = doc[pdf_page_number]

        # ページ番号の抽出
        page_number = None
        blocks = page.get_text("blocks", sort=True)
        for block in reversed(blocks):
            text = block[4].strip()

            match = re.fullmatch(
                r'[-－−–—]\s*(\d+)\s*[-－−–—]',
                text
            )

            if match:
                page_number = int(match.group(1))
                break

        text = page.get_text("text", sort=True)
        if page_number is not None:
            student_handbook_pages.append({
                        "page_number": page_number,
                        "pdf_page_number": pdf_page_number,
                        "text": text
            })
    doc.close()

except Exception as e:
    print(f"Error opening PDF file: {e}")
    exit(1)

# ページごとにテキストをチャンクに分割する
student_handbook_chunks = []
for page in student_handbook_pages:
    text_split = [
        sentence.strip()
        for sentence in re.split(r"。", page["text"])
        if sentence.strip()
    ]
    idx = 0
    while idx < len(text_split):
        chunk = ""
        while idx < len(text_split) and len(chunk) + len(text_split[idx]) + 1 <= chunk_size:
            chunk += text_split[idx] + "。"
            idx += 1
        if len(chunk) == 0:
            split = [text_split[idx][i:i+chunk_size] for i in range(0, len(text_split[idx]), chunk_size)]
            idx += 1
            for s in split:
                student_handbook_chunks.append({
                    "chunk_id": len(student_handbook_chunks),
                    "page_number": page["page_number"],
                    "pdf_page_number": page["pdf_page_number"],
                    "text": s
                })
        else:
            student_handbook_chunks.append({
                "chunk_id": len(student_handbook_chunks),
                "page_number": page["page_number"],
                "pdf_page_number": page["pdf_page_number"],
                "text": chunk
            })

#jsonファイルに保存する        
output_path = Path(chunk_output_path)
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as file:
    json.dump(
        student_handbook_chunks,
        file,
        ensure_ascii=False,
        indent=2,
    )