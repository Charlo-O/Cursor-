#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
表格尺寸分析脚本
该脚本用于分析表格中的"size"列，统计不同尺寸的出现次数
支持Excel(.xlsx, .xls)和CSV格式
"""

import pandas as pd
import os
import argparse
from collections import Counter
import matplotlib.pyplot as plt


def analyze_size_column(file_path, sheet_name=0, size_column='size', output_file=None):
    """
    分析表格中的尺寸列并统计各尺寸的出现次数
    
    参数:
        file_path (str): 表格文件路径
        sheet_name (str or int): Excel工作表名称或索引，默认为第一个工作表
        size_column (str): 包含尺寸信息的列名，默认为'size'
        output_file (str): 输出结果的文件路径，默认为None（仅打印结果）
    
    返回:
        dict: 包含尺寸和对应数量的字典
    """
    # 根据文件类型读取表格
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif file_ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}。请使用Excel(.xlsx, .xls)或CSV文件。")
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return None
    
    # 检查size列是否存在
    if size_column not in df.columns:
        print(f"错误: '{size_column}'列在表格中不存在。")
        print(f"可用的列有: {', '.join(df.columns)}")
        return None
    
    # 统计size列中各尺寸的出现次数
    size_counts = Counter(df[size_column].astype(str))
    
    # 按数量排序（从高到低）
    sorted_sizes = dict(sorted(size_counts.items(), key=lambda x: x[1], reverse=True))
    
    # 输出结果
    print("\n尺寸分析结果:")
    print("-" * 30)
    print(f"{'尺寸':<15}数量")
    print("-" * 30)
    
    for size, count in sorted_sizes.items():
        print(f"{size:<15}{count}")
    
    # 保存结果到文件
    if output_file:
        result_df = pd.DataFrame({
            '尺寸': list(sorted_sizes.keys()),
            '数量': list(sorted_sizes.values())
        })
        
        output_ext = os.path.splitext(output_file)[1].lower()
        if output_ext in ['.xlsx', '.xls']:
            result_df.to_excel(output_file, index=False)
        else:
            result_df.to_csv(output_file, index=False)
        
        print(f"\n结果已保存至: {output_file}")
    
    # 生成图表
    create_size_chart(sorted_sizes)
    
    return sorted_sizes


def create_size_chart(size_counts, save_path=None):
    """
    根据尺寸统计创建可视化图表
    
    参数:
        size_counts (dict): 包含尺寸和对应数量的字典
        save_path (str): 图表保存路径，默认为None（仅显示不保存）
    """
    # 如果尺寸过多，只显示前10个
    if len(size_counts) > 10:
        top_sizes = dict(list(size_counts.items())[:10])
        plt.figure(figsize=(10, 6))
        plt.bar(top_sizes.keys(), top_sizes.values())
        plt.title('前10个尺寸的分布情况')
    else:
        plt.figure(figsize=(10, 6))
        plt.bar(size_counts.keys(), size_counts.values())
        plt.title('尺寸分布情况')
    
    plt.xlabel('尺寸')
    plt.ylabel('数量')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"图表已保存至: {save_path}")
    
    plt.show()


def main():
    parser = argparse.ArgumentParser(description='分析表格中的size列并统计各尺寸的出现次数')
    parser.add_argument('file', help='表格文件路径（支持Excel和CSV格式）')
    parser.add_argument('--sheet', '-s', default=0, help='Excel工作表名称或索引（对CSV文件无效）')
    parser.add_argument('--column', '-c', default='size', help='包含尺寸信息的列名（默认为"size"）')
    parser.add_argument('--output', '-o', help='输出结果的文件路径（可选）')
    parser.add_argument('--chart', '-g', help='保存图表的文件路径（可选，例如 chart.png）')
    
    args = parser.parse_args()
    
    size_counts = analyze_size_column(
        args.file, 
        sheet_name=args.sheet,
        size_column=args.column,
        output_file=args.output
    )
    
    if size_counts and args.chart:
        create_size_chart(size_counts, args.chart)


if __name__ == "__main__":
    main() 