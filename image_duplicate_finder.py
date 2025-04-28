import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import imagehash
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from collections import defaultdict
import threading
import time
from functools import partial

class ImageDuplicateFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("图片重复查找器")
        self.root.geometry("900x600")
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        
        # 创建变量
        self.folder_path = tk.StringVar()
        self.status_text = tk.StringVar()
        self.status_text.set("就绪")
        self.similarity_threshold = tk.IntVar(value=90)  # 默认相似度阈值为90%
        self.comparison_method = tk.StringVar(value="phash")  # 默认使用感知哈希
        
        # 创建UI组件
        self.create_widgets()
        
        # 存储数据
        self.image_hashes = {}  # 保存图像哈希值或直方图
        self.image_data = {}    # 保存图像数据(用于SSIM)
        self.duplicate_groups = []  # 保存找到的重复图像组
        self.current_group_index = 0  # 当前查看的重复组索引
        
        # 当前显示的图像
        self.current_images = []
        self.current_image_paths = []
        
    def create_widgets(self):
        # 顶部框架 - 文件夹选择
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        
        ttk.Label(top_frame, text="选择文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(top_frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(top_frame, text="浏览", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 算法选择
        algorithm_frame = ttk.Frame(self.root, padding=5)
        algorithm_frame.pack(fill="x")
        
        ttk.Label(algorithm_frame, text="比较算法:").pack(side="left", padx=5)
        ttk.Radiobutton(algorithm_frame, text="感知哈希", variable=self.comparison_method, 
                       value="phash").pack(side="left", padx=10)
        ttk.Radiobutton(algorithm_frame, text="颜色直方图", variable=self.comparison_method, 
                       value="histogram").pack(side="left", padx=10)
        ttk.Radiobutton(algorithm_frame, text="结构相似性(SSIM)", variable=self.comparison_method, 
                       value="ssim").pack(side="left", padx=10)
        
        # 相似度阈值设置
        similarity_frame = ttk.Frame(self.root, padding=5)
        similarity_frame.pack(fill="x")
        
        ttk.Label(similarity_frame, text="相似度阈值:").pack(side="left", padx=5)
        ttk.Scale(similarity_frame, from_=1, to=100, variable=self.similarity_threshold, 
                 orient="horizontal", length=300).pack(side="left", padx=5)
        ttk.Label(similarity_frame, text=lambda: f"{self.similarity_threshold.get()}%").pack(side="left")
        
        # 按钮框架
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="扫描图片", command=self.start_scan).pack(side="left", padx=5)
        ttk.Button(button_frame, text="上一组", command=self.show_previous_group).pack(side="left", padx=5)
        ttk.Button(button_frame, text="下一组", command=self.show_next_group).pack(side="left", padx=5)
        
        # 状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_text, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
        
        # 中间框架 - 图像显示
        self.image_frame = ttk.Frame(self.root, padding=10)
        self.image_frame.pack(fill="both", expand=True)
        
        # 设置进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(side="bottom", fill="x", padx=10, pady=5)
        
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.status_text.set(f"已选择文件夹: {folder_selected}")
    
    def start_scan(self):
        if not self.folder_path.get():
            messagebox.showerror("错误", "请先选择一个文件夹")
            return
        
        # 清除上一次结果
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        
        self.duplicate_groups = []
        self.current_group_index = 0
        
        # 使用线程避免界面冻结
        method = self.comparison_method.get()
        self.status_text.set(f"开始扫描图片... 使用{self.get_method_name(method)}算法")
        scan_thread = threading.Thread(target=self.scan_images)
        scan_thread.daemon = True
        scan_thread.start()
    
    def get_method_name(self, method):
        if method == "phash":
            return "感知哈希"
        elif method == "histogram":
            return "颜色直方图"
        elif method == "ssim":
            return "结构相似性(SSIM)"
        return "未知"
    
    def calculate_histogram(self, img):
        """计算彩色图像的直方图特征"""
        # 将图像转换为BGR格式（OpenCV使用BGR）
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # 转换为HSV空间
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # 计算HSV直方图
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        
        # 归一化直方图
        cv2.normalize(hist, hist, 0, 1.0, cv2.NORM_MINMAX)
        
        return hist.flatten()
    
    def compare_histograms(self, hist1, hist2):
        """比较两个直方图，返回相似度百分比"""
        # 使用相关性方法比较直方图
        # 相关性方法返回范围为[-1, 1]的值，1表示完全匹配
        correlation = cv2.compareHist(hist1.reshape(-1, 1), hist2.reshape(-1, 1), cv2.HISTCMP_CORREL)
        
        # 将相关性转换为百分比相似度(范围0-100)
        similarity = max(0, (correlation + 1) / 2 * 100)
        
        return similarity
    
    def prepare_for_ssim(self, img):
        """准备图像用于SSIM比较，统一大小并转为灰度"""
        # 调整图像大小为标准尺寸(64x64)
        img_resized = img.resize((64, 64), Image.LANCZOS)
        
        # 转换为灰度图
        if img_resized.mode != 'L':
            img_gray = img_resized.convert('L')
        else:
            img_gray = img_resized
            
        # 转换为numpy数组
        return np.array(img_gray)
    
    def compare_ssim(self, img1, img2):
        """使用SSIM比较两个图像，返回相似度百分比"""
        # 计算SSIM，范围为[-1, 1]
        ssim_score = ssim(img1, img2)
        
        # 转换为百分比相似度(范围0-100)
        similarity = max(0, (ssim_score + 1) / 2 * 100)
        
        return similarity
    
    def scan_images(self):
        folder = self.folder_path.get()
        self.image_hashes = {}
        self.image_data = {}
        method = self.comparison_method.get()
        
        # 获取所有图像文件
        all_files = []
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
        
        for root, _, files in os.walk(folder):
            for file in files:
                if os.path.splitext(file)[1].lower() in supported_formats:
                    all_files.append(os.path.join(root, file))
        
        total_files = len(all_files)
        if total_files == 0:
            self.root.after(0, lambda: messagebox.showinfo("结果", "文件夹中没有图像文件"))
            self.root.after(0, lambda: self.status_text.set("扫描完成：没有找到图像"))
            return
        
        # 计算每个图像的特征（哈希值或直方图或SSIM数据）
        for i, file_path in enumerate(all_files):
            try:
                # 更新进度
                progress_percent = (i + 1) / total_files * 100
                self.root.after(0, lambda p=progress_percent: self.progress.configure(value=p))
                self.root.after(0, lambda m=f"扫描中... {i+1}/{total_files}": self.status_text.set(m))
                
                # 根据所选方法计算特征
                with Image.open(file_path) as img:
                    if method == "phash":
                        # 使用感知哈希
                        feature = imagehash.phash(img)
                        self.image_hashes[file_path] = feature
                    elif method == "histogram":
                        # 使用颜色直方图
                        feature = self.calculate_histogram(img)
                        self.image_hashes[file_path] = feature
                    else:  # ssim
                        # 为SSIM准备图像数据
                        img_data = self.prepare_for_ssim(img)
                        self.image_data[file_path] = img_data
            except Exception as e:
                print(f"无法处理文件 {file_path}: {e}")
        
        # 查找相似图像
        if method == "phash":
            self.find_similar_images_phash()
        elif method == "histogram":
            self.find_similar_images_histogram()
        else:  # ssim
            self.find_similar_images_ssim()
        
        # 更新UI
        self.root.after(0, lambda: self.progress.configure(value=100))
        self.root.after(0, lambda: self.show_results())
    
    def find_similar_images_phash(self):
        """使用感知哈希查找相似图像"""
        similarity_threshold = self.similarity_threshold.get()
        hash_dict = defaultdict(list)
        
        # 首先对完全相同的哈希值进行分组
        for path, hash_value in self.image_hashes.items():
            hash_dict[hash_value].append(path)
        
        # 收集完全相同的图像
        exact_duplicates = [paths for paths in hash_dict.values() if len(paths) > 1]
        
        # 寻找相似的图像（不完全相同但相似度高）
        if similarity_threshold < 100:
            remaining_images = [path for paths in hash_dict.values() if len(paths) == 1 for path in paths]
            similarity_groups = []
            
            while remaining_images:
                current = remaining_images[0]
                current_hash = self.image_hashes[current]
                similar = [current]
                
                i = 1
                while i < len(remaining_images):
                    compare_path = remaining_images[i]
                    compare_hash = self.image_hashes[compare_path]
                    
                    # 计算哈希之间的差异
                    hash_diff = current_hash - compare_hash
                    max_diff = 64  # 64位哈希的最大差异
                    similarity = 100 - (hash_diff / max_diff * 100)
                    
                    if similarity >= similarity_threshold:
                        similar.append(compare_path)
                        remaining_images.pop(i)
                    else:
                        i += 1
                
                remaining_images.pop(0)
                if len(similar) > 1:
                    similarity_groups.append(similar)
            
            # 合并完全相同和相似的图像组
            self.duplicate_groups = exact_duplicates + similarity_groups
        else:
            self.duplicate_groups = exact_duplicates
    
    def find_similar_images_histogram(self):
        """使用直方图查找相似图像"""
        similarity_threshold = self.similarity_threshold.get()
        image_paths = list(self.image_hashes.keys())
        
        self.duplicate_groups = []
        processed = set()
        
        for i, path1 in enumerate(image_paths):
            if path1 in processed:
                continue
                
            hist1 = self.image_hashes[path1]
            similar_group = [path1]
            processed.add(path1)
            
            for path2 in image_paths[i+1:]:
                if path2 in processed:
                    continue
                    
                hist2 = self.image_hashes[path2]
                similarity = self.compare_histograms(hist1, hist2)
                
                if similarity >= similarity_threshold:
                    similar_group.append(path2)
                    processed.add(path2)
            
            if len(similar_group) > 1:
                self.duplicate_groups.append(similar_group)
    
    def find_similar_images_ssim(self):
        """使用SSIM查找相似图像"""
        similarity_threshold = self.similarity_threshold.get()
        image_paths = list(self.image_data.keys())
        
        self.duplicate_groups = []
        processed = set()
        
        # 更新状态为开始比较
        self.root.after(0, lambda: self.status_text.set("正在比较图像相似度..."))
        
        total_comparisons = len(image_paths) * (len(image_paths) - 1) // 2
        comparison_count = 0
        
        for i, path1 in enumerate(image_paths):
            if path1 in processed:
                continue
                
            img1 = self.image_data[path1]
            similar_group = [path1]
            processed.add(path1)
            
            for j, path2 in enumerate(image_paths[i+1:], i+1):
                if path2 in processed:
                    continue
                
                # 更新进度
                comparison_count += 1
                if comparison_count % 10 == 0:  # 每10次比较更新一次，避免UI过度更新
                    progress = min(100, comparison_count / total_comparisons * 100)
                    self.root.after(0, lambda p=progress: self.progress.configure(value=p))
                    self.root.after(0, lambda c=comparison_count, t=total_comparisons: 
                                   self.status_text.set(f"比较中... {c}/{t}"))
                
                # 比较图像
                img2 = self.image_data[path2]
                similarity = self.compare_ssim(img1, img2)
                
                if similarity >= similarity_threshold:
                    similar_group.append(path2)
                    processed.add(path2)
            
            if len(similar_group) > 1:
                self.duplicate_groups.append(similar_group)
    
    def show_results(self):
        if not self.duplicate_groups:
            self.status_text.set("未找到重复图像")
            messagebox.showinfo("结果", "未找到重复图像")
            return
        
        total_dupes = sum(len(group) for group in self.duplicate_groups)
        groups_count = len(self.duplicate_groups)
        self.status_text.set(f"找到 {groups_count} 组重复图像，共 {total_dupes} 张图片")
        
        # 显示第一组
        self.show_group(0)
    
    def show_group(self, group_index):
        if not self.duplicate_groups:
            return
        
        # 清除当前显示
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        
        self.current_group_index = group_index
        group = self.duplicate_groups[group_index]
        
        # 更新状态
        self.status_text.set(f"显示第 {group_index + 1}/{len(self.duplicate_groups)} 组 - {len(group)} 张相似图片")
        
        # 重置当前显示
        self.current_images = []
        self.current_image_paths = []
        
        # 创建一个画布框架
        canvas_frame = ttk.Frame(self.image_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        # 创建画布和滚动条
        canvas = tk.Canvas(canvas_frame)
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
        
        # 配置画布
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        
        # 创建显示框架
        display_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=display_frame, anchor="nw")
        
        # 每行显示的图像数
        images_per_row = 3
        max_height = 200
        
        # 显示每个图像
        for i, img_path in enumerate(group):
            row = i // images_per_row
            col = i % images_per_row
            
            # 创建图像框架
            img_frame = ttk.Frame(display_frame, borderwidth=2, relief="groove")
            img_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            try:
                # 打开并调整图像大小
                with Image.open(img_path) as img:
                    # 保持纵横比调整大小
                    width, height = img.size
                    ratio = min(200 / width, max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    img_resized = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # 创建Tkinter图像
                    tk_img = ImageTk.PhotoImage(img_resized)
                    self.current_images.append(tk_img)  # 保持引用以避免垃圾回收
                    self.current_image_paths.append(img_path)
                    
                    # 显示图像
                    img_label = ttk.Label(img_frame, image=tk_img)
                    img_label.pack(padx=5, pady=5)
                    
                    # 显示文件名和大小
                    file_name = os.path.basename(img_path)
                    file_size = os.path.getsize(img_path) / 1024  # KB
                    
                    info_text = f"文件名: {file_name}\n大小: {file_size:.1f} KB"
                    ttk.Label(img_frame, text=info_text, wraplength=200).pack(padx=5)
                    
                    # 添加删除按钮
                    ttk.Button(img_frame, text="删除", 
                              command=partial(self.delete_image, img_path)).pack(pady=5)
            except Exception as e:
                ttk.Label(img_frame, text=f"无法加载图像\n{os.path.basename(img_path)}\n错误: {str(e)}",
                         wraplength=200).pack(padx=10, pady=10)
        
        # 更新画布滚动区域
        display_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def show_previous_group(self):
        if self.duplicate_groups and self.current_group_index > 0:
            self.show_group(self.current_group_index - 1)
    
    def show_next_group(self):
        if self.duplicate_groups and self.current_group_index < len(self.duplicate_groups) - 1:
            self.show_group(self.current_group_index + 1)
    
    def delete_image(self, img_path):
        try:
            # 确认删除
            if messagebox.askyesno("确认删除", f"确定要删除图像\n{img_path}?"):
                os.remove(img_path)
                self.status_text.set(f"已删除: {os.path.basename(img_path)}")
                
                # 从当前组中移除
                current_group = self.duplicate_groups[self.current_group_index]
                current_group.remove(img_path)
                
                # 如果组为空，则移除组
                if not current_group:
                    self.duplicate_groups.pop(self.current_group_index)
                    if not self.duplicate_groups:
                        self.status_text.set("所有重复图像已处理")
                        for widget in self.image_frame.winfo_children():
                            widget.destroy()
                        return
                    
                    # 调整当前索引
                    if self.current_group_index >= len(self.duplicate_groups):
                        self.current_group_index = len(self.duplicate_groups) - 1
                
                # 刷新显示
                self.show_group(self.current_group_index)
        except Exception as e:
            messagebox.showerror("删除错误", f"无法删除图像: {str(e)}")

if __name__ == "__main__":
    try:
        # 检查必要的库
        import PIL
        import imagehash
        import cv2
        import numpy as np
        from skimage.metrics import structural_similarity
    except ImportError as e:
        print(f"缺少必要的库: {e}")
        print("请安装以下库:")
        print("pip install pillow imagehash opencv-python numpy scikit-image")
        import sys
        sys.exit(1)
        
    root = tk.Tk()
    app = ImageDuplicateFinder(root)
    root.mainloop() 