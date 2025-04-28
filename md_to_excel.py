import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import re
import os

class MarkdownToExcelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Markdown to Excel Converter")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 12))
        self.style.configure("TLabel", font=("Helvetica", 12))
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        title_label = ttk.Label(self.main_frame, text="Markdown to Excel Converter", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # 创建文件选择部分
        self.file_frame = ttk.LabelFrame(self.main_frame, text="文件选择", padding="10")
        self.file_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.md_file_path = tk.StringVar()
        self.excel_file_path = tk.StringVar()
        
        # Markdown文件选择
        ttk.Label(self.file_frame, text="Markdown文件:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(self.file_frame, textvariable=self.md_file_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.file_frame, text="浏览...", command=self.browse_md_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Excel保存位置
        ttk.Label(self.file_frame, text="保存Excel至:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(self.file_frame, textvariable=self.excel_file_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.file_frame, text="浏览...", command=self.browse_excel_location).grid(row=1, column=2, padx=5, pady=5)
        
        # 创建选项部分
        self.options_frame = ttk.LabelFrame(self.main_frame, text="转换选项", padding="10")
        self.options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        # 选项：是否仅提取表格
        self.tables_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.options_frame, text="仅提取Markdown表格", variable=self.tables_only).grid(row=0, column=0, sticky="w", pady=5)
        
        # 选项：是否包含标题
        self.include_headers = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.options_frame, text="包含表格标题", variable=self.include_headers).grid(row=0, column=1, sticky="w", pady=5)
        
        # 创建日志区域
        self.log_frame = ttk.LabelFrame(self.main_frame, text="转换日志", padding="10")
        self.log_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=10)
        self.main_frame.grid_rowconfigure(3, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = tk.Text(self.log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建按钮区域
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(self.button_frame, text="转换", command=self.convert_md_to_excel, width=15).grid(row=0, column=0, padx=10)
        ttk.Button(self.button_frame, text="退出", command=root.destroy, width=15).grid(row=0, column=1, padx=10)
        
        # 进度条
        self.progress = ttk.Progressbar(self.main_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)
    
    def browse_md_file(self):
        """浏览并选择Markdown文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.md_file_path.set(file_path)
            # 自动生成Excel保存路径（替换扩展名）
            excel_path = os.path.splitext(file_path)[0] + ".xlsx"
            self.excel_file_path.set(excel_path)
    
    def browse_excel_location(self):
        """浏览并选择Excel保存位置"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if file_path:
            self.excel_file_path.set(file_path)
    
    def log(self, message):
        """添加消息到日志区域"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def extract_tables_from_md(self, md_content):
        """从Markdown内容中提取表格"""
        tables = []
        lines = md_content.split('\n')
        
        i = 0
        while i < len(lines):
            # 查找表格开始位置（包含 | 的行）
            if '|' in lines[i]:
                table_start = i
                
                # 确认下一行是否为分隔行（包含 -|-）
                if i + 1 < len(lines) and re.match(r'\s*\|[-:\|\s]+\|\s*$', lines[i + 1]):
                    # 继续寻找表格结束位置
                    j = i + 2
                    while j < len(lines) and '|' in lines[j]:
                        j += 1
                    
                    table_end = j
                    current_table = lines[table_start:table_end]
                    
                    # 添加前一行作为表格标题（如果存在且选项开启）
                    table_title = None
                    if self.include_headers.get() and table_start > 0 and lines[table_start-1].strip() and not '|' in lines[table_start-1]:
                        table_title = lines[table_start-1].strip()
                    
                    tables.append((current_table, table_title))
                    i = table_end
                else:
                    i += 1
            else:
                i += 1
        
        return tables
    
    def parse_md_table(self, table_lines):
        """解析Markdown表格内容为数据结构"""
        # 删除每行首尾的空白和可能的前后|符号
        cleaned_lines = [line.strip().strip('|').strip() for line in table_lines]
        
        # 解析表头和数据行
        headers = [cell.strip() for cell in cleaned_lines[0].split('|')]
        
        # 跳过分隔行（第二行）
        data_rows = []
        for line in cleaned_lines[2:]:
            if line.strip():  # 忽略空行
                row_data = [cell.strip() for cell in line.split('|')]
                data_rows.append(row_data)
        
        return headers, data_rows
    
    def convert_md_to_excel(self):
        """将Markdown文件转换为Excel"""
        md_path = self.md_file_path.get()
        excel_path = self.excel_file_path.get()
        
        if not md_path or not excel_path:
            messagebox.showerror("错误", "请选择Markdown文件和Excel保存位置")
            return
        
        try:
            self.log(f"开始转换: {md_path}")
            self.progress['value'] = 10
            
            # 读取Markdown文件
            with open(md_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            
            self.progress['value'] = 30
            self.log("读取Markdown文件完成，开始解析...")
            
            # 提取表格
            tables = self.extract_tables_from_md(md_content)
            
            if not tables:
                self.log("警告: 未找到Markdown表格")
                messagebox.showwarning("警告", "未找到Markdown表格")
                self.progress['value'] = 0
                return
            
            self.log(f"找到 {len(tables)} 个表格，准备转换...")
            self.progress['value'] = 50
            
            # 创建Excel写入器
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for i, (table_lines, title) in enumerate(tables):
                    headers, data_rows = self.parse_md_table(table_lines)
                    
                    # 创建DataFrame
                    df = pd.DataFrame(data_rows, columns=headers)
                    
                    # 确定表格名称
                    sheet_name = f"Table_{i+1}"
                    if title:
                        # 移除不合法的Excel工作表名称字符
                        sheet_name = re.sub(r'[\\/*?:\[\]]', '_', title)
                        # 截断长度（Excel工作表名称最大31个字符）
                        sheet_name = sheet_name[:31]
                    
                    # 写入Excel
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    self.log(f"表格 '{sheet_name}' 已写入...")
                    
                    # 更新进度条
                    self.progress['value'] = 50 + (i + 1) * 40 / len(tables)
            
            self.progress['value'] = 100
            self.log(f"转换完成! 已保存至: {excel_path}")
            messagebox.showinfo("成功", f"转换完成! 已保存至:\n{excel_path}")
            
        except Exception as e:
            self.log(f"错误: {str(e)}")
            messagebox.showerror("错误", f"转换过程中出错:\n{str(e)}")
        finally:
            self.progress['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = MarkdownToExcelApp(root)
    root.mainloop() 