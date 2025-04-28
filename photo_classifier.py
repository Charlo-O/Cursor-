import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import json
import requests
from PIL import Image, ImageTk
import io

class PhotoClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("照片主题分类工具")
        self.root.geometry("800x600")
        
        # 设置主题分类列表
        self.themes = [
            "1. 生日祝福 (各年龄/里程碑/1岁)",
            "2. 毕业祝贺 (各学段/年份/个性化)",
            "3. 迎婴派对与欢迎宝宝 (含性别揭示)",
            "4. 婚前派对 (订婚/新娘送礼/告别单身等)",
            "5. 结婚纪念日 (通用及特定年份)",
            "6. 退休庆祝 (含趣味标语)",
            "7. 圣诞节 (传统与宗教)",
            "8. 新年庆祝 (通用及特定年份)",
            "9. 复活节 (通用与宗教)",
            "10. 万圣节",
            "11. 感恩节",
            "12. 情人节",
            "13. 父母节 (母亲节/父亲节合并)",
            "14. 美国节日 (爱国主题/劳动节等)",
            "15. 欢迎回家 (通用与军人)",
            "16. 欢送/祝福好运 (告别/新工作/新篇章)",
            "17. 宗教仪式/成人礼/标志 (跨信仰)",
            "18. 犹太教节日 (光明节/逾越节/新年等)",
            "19. 伊斯兰教节日 (斋月/开斋节)",
            "20. LGBTQ+ 骄傲与支持 (含各类旗帜)",
            "21. 多元文化节日庆典 (春节/五月五/六月节/亡灵节/排灯节/圣帕特里克节等)",
            "22. 乔迁/新家祝福",
            "23. 社会关怀与意识提升 (健康/环保/特殊群体)",
            "24. 文化遗产/历史纪念月份 (如非裔/西裔)",
            "25. 主题派对 (赛车/海盗/动物/可爱风等)",
            "26. 个性化定制选项 (照片/姓名/文字/设计)",
            "27. 照片展示横幅 (如宝宝月度里程碑)",
            "28. 宠物庆祝 (领养日)",
            "29. 大型体育赛事 (如奥运会)",
            "30. 教堂欢迎横幅"
        ]
        
        # 豆包API配置
        self.api_key = ""  # 豆包模型API Bearer Token
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"  # 豆包API URL
        self.model = "doubao-1.5-vision-pro-32k-250115"  # 豆包视觉模型
        
        # 创建GUI组件
        self.create_widgets()
        
        # 图片处理变量
        self.selected_folder = ""
        self.image_files = []
        self.processing = False
        self.current_image_index = 0
        self.classified_images = {}  # 分类结果: {theme_name: [image_paths]}
    
    def create_widgets(self):
        # 创建顶部框架
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 选择文件夹按钮
        self.folder_btn = tk.Button(top_frame, text="选择照片文件夹", command=self.select_folder)
        self.folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 显示所选文件夹路径
        self.folder_path_var = tk.StringVar()
        self.folder_path_var.set("未选择文件夹")
        folder_path_label = tk.Label(top_frame, textvariable=self.folder_path_var, width=50, anchor="w")
        folder_path_label.pack(side=tk.LEFT, padx=5)
        
        # 开始分类按钮
        self.start_btn = tk.Button(top_frame, text="开始分类", command=self.start_classification, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # API密钥输入框
        api_frame = tk.Frame(self.root)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(api_frame, text="豆包API密钥:").pack(side=tk.LEFT, padx=5)
        self.api_key_entry = tk.Entry(api_frame, width=50, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5)
        
        # 模型选择下拉菜单
        tk.Label(api_frame, text="模型:").pack(side=tk.LEFT, padx=5)
        self.model_var = tk.StringVar()
        self.model_var.set(self.model)
        model_dropdown = ttk.Combobox(api_frame, textvariable=self.model_var, width=30)
        model_dropdown['values'] = (
            "doubao-1.5-vision-pro-32k-250115",
            "doubao-1.1-vision-250105",
            "doubao-1.5-vision-250315"
        )
        model_dropdown.pack(side=tk.LEFT, padx=5)
        
        # 创建中间的图片预览区域
        preview_frame = tk.Frame(self.root)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 图片显示
        self.image_label = tk.Label(preview_frame, text="图片预览区域", bg="lightgray", height=10)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(progress_frame, text="处理进度:").pack(side=tk.LEFT, padx=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=500)
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.progress_text = tk.StringVar()
        self.progress_text.set("0/0")
        tk.Label(progress_frame, textvariable=self.progress_text, width=10).pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        results_frame = tk.Frame(self.root)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 结果滚动列表
        scrollbar = tk.Scrollbar(results_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_listbox = tk.Listbox(results_frame, height=8, width=80, yscrollcommand=scrollbar.set)
        self.results_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_listbox.yview)
        
        # 底部按钮区域
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.save_btn = tk.Button(bottom_frame, text="保存分类结果", command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_results_btn = tk.Button(bottom_frame, text="查看分类结果", command=self.view_results, state=tk.DISABLED)
        self.view_results_btn.pack(side=tk.LEFT, padx=5)
        
        # 新增一个专门的分类到文件夹的按钮
        self.organize_btn = tk.Button(bottom_frame, text="分类到文件夹", command=self.organize_to_folders, state=tk.DISABLED)
        self.organize_btn.pack(side=tk.LEFT, padx=5)
    
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="选择照片文件夹")
        if folder_path:
            self.selected_folder = folder_path
            self.folder_path_var.set(folder_path)
            self.scan_image_files()
    
    def scan_image_files(self):
        """扫描选择的文件夹中的所有图片文件"""
        self.image_files = []
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
        
        try:
            for root, _, files in os.walk(self.selected_folder):
                for file in files:
                    if file.lower().endswith(valid_extensions):
                        full_path = os.path.join(root, file)
                        self.image_files.append(full_path)
            
            if self.image_files:
                self.results_listbox.delete(0, tk.END)
                self.results_listbox.insert(tk.END, f"找到 {len(self.image_files)} 个图片文件")
                self.start_btn.config(state=tk.NORMAL)
            else:
                messagebox.showinfo("提示", "所选文件夹中没有找到图片文件")
                self.start_btn.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("错误", f"扫描文件夹时出错: {str(e)}")
            self.start_btn.config(state=tk.DISABLED)
    
    def start_classification(self):
        """开始分类处理"""
        if not self.image_files:
            messagebox.showinfo("提示", "没有图片可以处理")
            return
        
        # 获取API密钥
        self.api_key = self.api_key_entry.get().strip()
        if not self.api_key:
            messagebox.showwarning("警告", "请输入豆包API密钥")
            return
        
        # 获取选择的模型
        self.model = self.model_var.get().strip()
        if not self.model:
            messagebox.showwarning("警告", "请选择模型")
            return
        
        # 重置分类结果
        self.classified_images = {theme: [] for theme in self.themes}
        self.current_image_index = 0
        self.progress_var.set(0)
        self.progress_text.set(f"0/{len(self.image_files)}")
        self.results_listbox.delete(0, tk.END)
        
        # 禁用按钮
        self.start_btn.config(state=tk.DISABLED)
        self.folder_btn.config(state=tk.DISABLED)
        self.processing = True
        
        # 在后台线程中处理，避免GUI卡顿
        threading.Thread(target=self.process_images, daemon=True).start()
    
    def process_images(self):
        """处理所有图片（在后台线程中运行）"""
        total_images = len(self.image_files)
        
        for i, image_path in enumerate(self.image_files):
            if not self.processing:
                break
                
            try:
                # 更新UI（在主线程中）
                self.root.after(0, self.update_progress, i, total_images)
                self.root.after(0, self.update_preview, image_path)
                
                # 调用豆包API进行分类
                theme = self.classify_image(image_path)
                
                # 记录分类结果
                if theme in self.classified_images:
                    self.classified_images[theme].append(image_path)
                else:
                    # 如果返回的主题不在预定义列表中，归类为"未分类"
                    if "未分类" not in self.classified_images:
                        self.classified_images["未分类"] = []
                    self.classified_images["未分类"].append(image_path)
                
                # 更新结果列表（在主线程中）
                self.root.after(0, self.update_results, image_path, theme)
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "错误", f"处理图片时出错: {str(e)}")
        
        # 完成处理
        self.root.after(0, self.finish_processing)
    
    def classify_image(self, image_path):
        """调用豆包API对图片进行分类"""
        try:
            # 读取图片文件
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # 准备API请求
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # 使用base64编码图片
            import base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # 根据火山引擎文档构建正确的请求体
            payload = {
                "model": self.model,  # 使用用户选择的模型
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "这张图片属于下面哪个主题分类？请只回答分类编号及名称，不要解释原因。\n" + "\n".join(self.themes)
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ]
            }
            
            # 发送API请求
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # 解析API响应
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                print(f"API返回结果: {content}")  # 调试信息
                
                # 解析回复内容，寻找主题编号
                for theme in self.themes:
                    theme_number = theme.split('.')[0].strip()
                    theme_name = theme.split('. ')[1].split(' ')[0] if '. ' in theme else ""
                    
                    # 检查主题编号或主题名称是否在内容中
                    if theme_number in content or (theme_name and theme_name in content):
                        return theme
                
                # 如果没有找到匹配的主题，返回一个默认主题
                return "未分类"
            else:
                # API请求失败，解析错误信息
                error_info = "未知错误"
                try:
                    error_json = response.json()
                    error_type = error_json.get("type", "")
                    error_code = error_json.get("code", "")
                    error_message = error_json.get("message", "")
                    error_info = f"{error_type}.{error_code}: {error_message}"
                except:
                    error_info = f"HTTP错误: {response.status_code}, {response.text}"
                
                print(f"API请求失败: {error_info}")  # 调试信息
                
                return f"API错误: {error_info}"
                
        except Exception as e:
            print(f"分类图片时出错: {str(e)}")
            return f"处理错误: {str(e)}"
    
    def update_progress(self, current, total):
        """更新进度条"""
        progress = (current + 1) / total * 100
        self.progress_var.set(progress)
        self.progress_text.set(f"{current + 1}/{total}")
    
    def update_preview(self, image_path):
        """更新图片预览"""
        try:
            # 打开图片并调整大小以适应预览区域
            img = Image.open(image_path)
            img.thumbnail((400, 300))  # 调整图片大小
            photo = ImageTk.PhotoImage(img)
            
            # 更新图片显示
            self.image_label.config(image=photo)
            self.image_label.image = photo  # 保持引用以防止垃圾回收
        except Exception as e:
            print(f"更新预览时出错: {str(e)}")
            self.image_label.config(image=None, text="无法预览图片")
    
    def update_results(self, image_path, theme):
        """更新结果列表"""
        filename = os.path.basename(image_path)
        self.results_listbox.insert(tk.END, f"{filename} -> {theme}")
        self.results_listbox.see(tk.END)  # 滚动到最新结果
    
    def finish_processing(self):
        """完成处理"""
        self.processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.folder_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.view_results_btn.config(state=tk.NORMAL)
        self.organize_btn.config(state=tk.NORMAL)  # 启用分类到文件夹按钮
        
        # 显示统计信息
        self.results_listbox.insert(tk.END, "-" * 50)
        self.results_listbox.insert(tk.END, "分类统计:")
        
        for theme in sorted(self.classified_images.keys()):
            count = len(self.classified_images.get(theme, []))
            if count > 0:
                self.results_listbox.insert(tk.END, f"{theme}: {count}张图片")
        
        messagebox.showinfo("处理完成", f"已完成 {len(self.image_files)} 张图片的分类")
    
    def save_results(self):
        """保存分类结果"""
        if not self.classified_images:
            messagebox.showinfo("提示", "没有分类结果可保存")
            return
        
        # 选择保存路径
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="保存分类结果"
        )
        
        if not save_path:
            return
        
        try:
            # 将分类结果保存为JSON文件
            result_data = {}
            for theme, images in self.classified_images.items():
                if images:  # 只保存有图片的分类
                    result_data[theme] = images
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("保存成功", f"分类结果已保存到: {save_path}")
            
            # 询问是否同时创建分类文件夹
            if messagebox.askyesno("创建文件夹", "是否要同时创建分类文件夹并整理图片？"):
                self.create_categorized_folders(os.path.dirname(save_path))
            
        except Exception as e:
            messagebox.showerror("保存失败", f"保存分类结果时出错: {str(e)}")
    
    def organize_to_folders(self):
        """直接将图片分类到文件夹（专用按钮）"""
        if not self.classified_images:
            messagebox.showinfo("提示", "没有分类结果可整理")
            return
        
        # 选择目标文件夹
        target_dir = filedialog.askdirectory(title="选择要保存分类结果的文件夹")
        if not target_dir:
            return
        
        # 询问用户是复制还是移动文件
        action = messagebox.askyesno("操作选择", "是否移动文件到分类文件夹？\n选择\"是\"将移动文件，选择\"否\"将复制文件", icon='question')
        
        # 创建并整理文件夹
        self.create_categorized_folders(target_dir, move_files=action)
    
    def create_categorized_folders(self, base_path, move_files=False):
        """创建分类文件夹并整理图片
        
        Args:
            base_path: 保存分类文件夹的根目录
            move_files: 是否移动文件而不是复制
        """
        try:
            import shutil
            
            # 创建分类文件夹的根目录
            categorized_dir = os.path.join(base_path, "分类结果")
            os.makedirs(categorized_dir, exist_ok=True)
            
            # 创建进度对话框
            progress_window = tk.Toplevel(self.root)
            progress_window.title("正在整理文件")
            progress_window.geometry("400x100")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            progress_label = tk.Label(progress_window, text="正在整理文件到分类文件夹...")
            progress_label.pack(pady=10)
            
            file_progress = ttk.Progressbar(progress_window, length=350)
            file_progress.pack(pady=10)
            
            # 计算总文件数
            total_files = sum(len(files) for files in self.classified_images.values() if files)
            file_progress["maximum"] = total_files
            processed_files = 0
            
            # 为每个主题创建文件夹并整理图片
            for theme, images in self.classified_images.items():
                if not images:
                    continue
                
                # 创建主题文件夹
                if theme in self.themes:
                    theme_number = theme.split('.')[0]
                    theme_name = theme.split('. ')[1].split(' ')[0]
                    folder_name = f"{theme_number}-{theme_name}"
                else:
                    # 处理未分类或其他非预定义主题
                    folder_name = "未分类"
                
                theme_dir = os.path.join(categorized_dir, folder_name)
                os.makedirs(theme_dir, exist_ok=True)
                
                # 处理图片
                for image_path in images:
                    dest_path = os.path.join(theme_dir, os.path.basename(image_path))
                    
                    # 更新进度
                    processed_files += 1
                    file_progress["value"] = processed_files
                    progress_label.config(text=f"正在处理: {os.path.basename(image_path)}")
                    progress_window.update()
                    
                    # 复制或移动文件
                    if move_files:
                        # 如果目标文件已存在，先删除
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        shutil.move(image_path, dest_path)
                    else:
                        shutil.copy2(image_path, dest_path)
            
            # 关闭进度窗口
            progress_window.destroy()
            
            action_word = "移动" if move_files else "复制"
            messagebox.showinfo("整理完成", f"已成功将照片{action_word}到分类文件夹: {categorized_dir}")
            
            # 如果是移动操作，更新图片路径
            if move_files:
                for theme, images in self.classified_images.items():
                    if not images:
                        continue
                    
                    # 获取主题文件夹名
                    if theme in self.themes:
                        theme_number = theme.split('.')[0]
                        theme_name = theme.split('. ')[1].split(' ')[0]
                        folder_name = f"{theme_number}-{theme_name}"
                    else:
                        folder_name = "未分类"
                    
                    theme_dir = os.path.join(categorized_dir, folder_name)
                    
                    # 更新路径
                    for i, old_path in enumerate(images[:]):
                        new_path = os.path.join(theme_dir, os.path.basename(old_path))
                        self.classified_images[theme][i] = new_path
                
                # 如果是从源文件夹移动走了所有文件，可能需要更新UI状态
                if not os.listdir(self.selected_folder) and self.selected_folder != categorized_dir:
                    messagebox.showinfo("提示", "原文件夹已空，所有照片已移动到分类文件夹")
            
        except Exception as e:
            messagebox.showerror("整理失败", f"创建分类文件夹并整理图片时出错: {str(e)}")
    
    def view_results(self):
        """查看分类结果"""
        if not self.classified_images:
            messagebox.showinfo("提示", "没有分类结果可查看")
            return
        
        # 创建新窗口显示分类结果
        results_window = tk.Toplevel(self.root)
        results_window.title("分类结果查看")
        results_window.geometry("800x600")
        
        # 创建分类列表和图片预览区域
        split_frame = tk.PanedWindow(results_window, orient=tk.HORIZONTAL)
        split_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧分类列表
        left_frame = tk.Frame(split_frame)
        
        tk.Label(left_frame, text="分类主题:").pack(anchor=tk.W, padx=5, pady=5)
        
        # 分类主题列表
        scrollbar = tk.Scrollbar(left_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        themes_listbox = tk.Listbox(left_frame, yscrollcommand=scrollbar.set, width=40)
        themes_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=themes_listbox.yview)
        
        # 添加主题列表
        for theme in sorted(self.classified_images.keys()):
            count = len(self.classified_images.get(theme, []))
            if count > 0:
                themes_listbox.insert(tk.END, f"{theme} ({count}张)")
        
        # 右侧图片列表
        right_frame = tk.Frame(split_frame)
        
        tk.Label(right_frame, text="图片列表:").pack(anchor=tk.W, padx=5, pady=5)
        
        # 图片列表
        scrollbar2 = tk.Scrollbar(right_frame)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        images_listbox = tk.Listbox(right_frame, yscrollcommand=scrollbar2.set)
        images_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar2.config(command=images_listbox.yview)
        
        # 图片预览
        preview_frame = tk.Frame(right_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        preview_label = tk.Label(preview_frame, text="选择图片预览", bg="lightgray", height=10)
        preview_label.pack(fill=tk.BOTH, expand=True)
        
        # 添加到分割窗口
        split_frame.add(left_frame)
        split_frame.add(right_frame)
        
        # 主题选择事件
        def on_theme_select(event):
            # 清空图片列表
            images_listbox.delete(0, tk.END)
            
            # 获取选中的主题
            selected_idx = themes_listbox.curselection()
            if not selected_idx:
                return
                
            selected_theme = themes_listbox.get(selected_idx[0]).split(" (")[0]
            
            # 显示该主题下的图片
            for image_path in self.classified_images.get(selected_theme, []):
                images_listbox.insert(tk.END, os.path.basename(image_path))
        
        # 图片选择事件
        def on_image_select(event):
            # 获取选中的图片
            selected_idx = images_listbox.curselection()
            if not selected_idx:
                return
                
            selected_image = images_listbox.get(selected_idx[0])
            
            # 获取当前主题
            theme_idx = themes_listbox.curselection()
            if not theme_idx:
                return
                
            selected_theme = themes_listbox.get(theme_idx[0]).split(" (")[0]
            
            # 查找完整路径
            for image_path in self.classified_images.get(selected_theme, []):
                if os.path.basename(image_path) == selected_image:
                    # 显示图片预览
                    try:
                        img = Image.open(image_path)
                        img.thumbnail((400, 300))  # 调整图片大小
                        photo = ImageTk.PhotoImage(img)
                        
                        preview_label.config(image=photo)
                        preview_label.image = photo  # 保持引用以防止垃圾回收
                    except Exception as e:
                        preview_label.config(image=None, text=f"无法预览图片: {str(e)}")
                    break
        
        # 绑定事件
        themes_listbox.bind('<<ListboxSelect>>', on_theme_select)
        images_listbox.bind('<<ListboxSelect>>', on_image_select)
    
    def on_closing(self):
        """关闭应用程序"""
        if self.processing:
            if messagebox.askyesno("确认", "正在处理图片，确定要退出吗？"):
                self.processing = False
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoClassifierApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop() 