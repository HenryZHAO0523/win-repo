# xlsx_to_csv.py
import pandas as pd
import os
import re

# ---------- 配置 ----------
xlsx_path = 'device_info.xlsx'   # 改成你的文件名（或绝对路径）
csv_path = 'device_info.csv'
header_row = 5                     # 第6行是表头 -> header=5
needed_cols = ["设备名称", "设备编码", "诊疗项目编码", "备注", "Hospital Code", "FTP Address", "Database URL", "Database PWD", "AHIS Code", "AHIS AppKey", "AHIS PWD", "RegistrationCode", "StaffCode"]

# 如果 Excel 中 StaffCode 实际上是数值但你希望强制补齐前导零到固定长度（例如7位），将此设为 True 并设置 zfill_width
auto_zfill = False
zfill_width = 7
# ---------- 结束配置 ----------

# 1. 尝试以字符串读取（保留原始文本形式的前导0）
#    如果 Excel 的 StaffCode 是文本格式，这会直接保留 "0064721"。
df = pd.read_excel(xlsx_path, header=header_row, dtype=str)

# 2. 校验所需列是否存在
missing = [c for c in needed_cols if c not in df.columns]
if missing:
    raise ValueError(f"缺少列: {missing}. 可用列名为: {list(df.columns)}")

# 3. 只保留目标列
df = df[needed_cols]

# 4. 将所有缺失值 NaN -> 空字符串（非常关键）
df = df.fillna('')

# 5. 去除每个字符串前后空白（只对字符串操作）
def safe_strip(x):
    if isinstance(x, str):
        return x.strip()
    # 防止出现 numpy.nan 等，统一返回空字符串
    if pd.isna(x):
        return ''
    return str(x).strip()

df = df.map(safe_strip)

# 6. 强力替换各种形式的“未找到” -> 置空
df = df.replace(r'^\s*未找到\s*$', '', regex=True)

# 7. 防止偶发的 'nan'/'None' 字符串残留（谨慎处理）
df = df.replace({'nan': '', 'NaN': '', 'None': ''})

# 8. 如果需要：对 StaffCode 做自动补零（仅在你明确打开开关时）
if auto_zfill:
    # 仅在内容为纯数字（或数字形式）时补零
    def zfill_if_numeric(s: str) -> str:
        if not isinstance(s, str) or s == '':
            return ''
        # 去掉小数点尾部 .0（若存在）
        if re.fullmatch(r'\d+\.0', s):
            s = s[:-2]
        # 只在全数字时补零
        if re.fullmatch(r'\d+', s):
            return s.zfill(zfill_width)
        return s
    df['StaffCode'] = df['StaffCode'].apply(zfill_if_numeric)

# 9. 关键：去掉“设备编码”和“诊疗项目编码”中误读成 xxx.0 的尾部 .0（保留前导0）
def clean_number(s: str) -> str:
    if not isinstance(s, str) or s == '':
        return ''
    # 如果形如 "123456.0" -> 去掉 .0
    if re.fullmatch(r'\d+\.0', s):
        return s[:-2]
    # 如果纯数字（含前导0），保留原样
    return s

for col in ["设备编码", "诊疗项目编码"]:
    df[col] = df[col].apply(clean_number)

# 10. 再次确保没有 NaN
df = df.fillna('')

# 11. 保存为 CSV（utf-8-sig，方便 Windows Excel 直接打开）
if os.path.exists(csv_path):
    try:
        os.remove(csv_path)  # 如果被占用会抛错，手动关闭 Excel 再试
    except PermissionError:
        raise PermissionError(f"无法删除旧文件 {csv_path} —— 请关闭它（例如在 Excel 中）后重试。")

df.to_csv(csv_path, index=False, encoding='utf-8-sig')

# 12. 简单校验并打印结果
contains_nan = df.map(lambda x: isinstance(x, str) and x.strip().lower() == 'nan').any().any()
print(f"已生成 {csv_path} 。表中是否仍含 'nan' 字样（应为 False）：{contains_nan}")
