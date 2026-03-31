import os
import re

# Tự động quét từ thư mục hiện tại (C:\Documents\BTL)
root_dir = os.getcwd() 
output_file = "copilot-instructions.md"

print(f"--- Đang quét toàn bộ repo Superpowers tại: {root_dir} ---")

skills_found = 0

with open(output_file, "w", encoding="utf-8") as outfile:
    outfile.write("# GLOBAL SUPERPOWERS RULES\n\n")
    outfile.write("Quy tắc: LUÔN tuân thủ các quy trình dưới đây khi được yêu cầu.\n\n")
    
    # Quét mọi ngóc ngách trong thư mục hiện tại
    for root, dirs, files in os.walk(root_dir):
        if "SKILL.md" in files:
            skill_name = os.path.basename(root)
            file_path = os.path.join(root, "SKILL.md")
            
            with open(file_path, "r", encoding="utf-8") as infile:
                content = infile.read()
                
                # BƯỚC QUAN TRỌNG: Cắt bỏ phần YAML Frontmatter (--- ... ---) ở đầu file
                content_clean = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
                
                outfile.write(f"## SKILL: {skill_name.upper()}\n\n")
                outfile.write(content_clean.strip())
                outfile.write("\n\n---\n\n")
                
            print(f"[OK] Đã dọn dẹp và gộp: {skill_name}")
            skills_found += 1

if skills_found > 0:
    print(f"\n--- THÀNH CÔNG! ---")
    print(f"Đã gộp {skills_found} kỹ năng vào file: {os.path.abspath(output_file)}")
else:
    print("\n[!] CẢNH BÁO: Không tìm thấy file SKILL.md nào.")
    print("Hãy chắc chắn bạn đã giải nén hoặc copy thư mục 'superpowers' vào trong C:\\Documents\\BTL")