# generate_configs.py
import os
import pandas as pd
import re
from lxml import etree

template_dir = 'template_configs'
output_dir = 'output'
device_info_path = 'device_info.csv'

# 读取 CSV（utf-8-sig），强制所有列为字符串，然后把 NaN 填成空字符串
df = pd.read_csv(device_info_path, encoding='utf-8-sig', dtype=str).fillna('')

def safe_str(val):
    if pd.isna(val):
        return ''
    s = str(val).strip()
    # 把类似 123.0 处理为 123
    if re.match(r'^\d+\.0$', s):
        return s[:-2]
    return s

# 公共字段（取 CSV 第二行，即 df.iloc[1]）
if len(df) > 0:
    global_row = df.iloc[0]
else:
    global_row = pd.Series()  # 防止只有一行时报错

# === 单独处理 imageDataHandler.cfg（只生成一个） ===
handler_src = os.path.join(template_dir, 'imageDataHandler.cfg')
handler_dst = r"D:\WORK\ConfigAutoModifier\output\imageDataHandler.cfg"

if os.path.exists(handler_src):
    handler_field_map = {
        'localAreaTag=': safe_str(global_row.get('Hospital Code', '')),
        'registrationCode=': safe_str(global_row.get('RegistrationCode', '')),
        'pacsDbConnectUrl=': safe_str(global_row.get('Database URL', '')),
        'pacsDbPasswd=': safe_str(global_row.get('Database PWD', '')),
        'apiAhisAreaTag=': safe_str(global_row.get('AHIS Code', '')),
        'apiAppKey=': safe_str(global_row.get('AHIS AppKey', '')),
        'apiAppSecret=': safe_str(global_row.get('AHIS PWD', '')),
        'defaultMentionOjStr=': safe_str(global_row.get('StaffCode', ''))
    }

    with open(handler_src, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        leading_ws_len = len(line) - len(line.lstrip('\r\n\t '))
        leading = line[:leading_ws_len]
        stripped = line.lstrip()

        replaced = False
        for key, value in handler_field_map.items():
            if stripped.startswith(key):
                new_lines.append(f"{leading}{key}{value}\n")
                replaced = True
                break

        if not replaced:
            new_lines.append(line)

    os.makedirs(os.path.dirname(handler_dst), exist_ok=True)
    with open(handler_dst, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"已生成全局 imageDataHandler.cfg：{handler_dst}")
else:
    print(f"模板缺失：{handler_src}（跳过）")

# === 单独处理 公共参数-0-全局业务参数【新】.txt（只生成一个） ===
global_txt_src = os.path.join(template_dir, '公共参数-0-全局业务参数【新】.txt')
global_txt_dst = os.path.join(output_dir, '公共参数-0-全局业务参数【新】.txt')

if os.path.exists(global_txt_src):

    global_field_map = {
        'localAreaTag=': safe_str(global_row.get('Hospital Code', '')),
        'apiAhisAreaTag=': safe_str(global_row.get('AHIS Code', '')),
        'apiAppKey=': safe_str(global_row.get('AHIS AppKey', '')),
        'apiAppSecret=': safe_str(global_row.get('AHIS PWD', ''))
    }

    with open(global_txt_src, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # 保留前导空格
        leading_ws_len = len(line) - len(line.lstrip('\r\n\t '))
        leading = line[:leading_ws_len]
        stripped = line.lstrip()

        replaced = False
        for key, value in global_field_map.items():
            if stripped.startswith(key):
                new_lines.append(f"{leading}{key}{value}\n")
                replaced = True
                break

        if not replaced:
            new_lines.append(line)

    os.makedirs(output_dir, exist_ok=True)

    with open(global_txt_dst, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"已生成全局业务参数文件：{global_txt_dst}")

else:
    print(f"模板缺失：{global_txt_src}（跳过）")

# 遍历每行
for idx, row in df.iterrows():
    # 安全获取并清理
    raw_name = row.get('设备名称', '')
    device_name = '' if pd.isna(raw_name) else str(raw_name).strip()
    device_code = '' if pd.isna(row.get('设备编码', '')) else str(row.get('设备编码', '')).strip()
    project_code = '' if pd.isna(row.get('诊疗项目编码', '')) else str(row.get('诊疗项目编码', '')).strip()

    # 额外防护：如果字符串恰好是 'nan'（小写或大写），视为空
    if device_name.lower() == 'nan':
        device_name = ''

    # 若设备名称为空则跳过（避免创建名为 '' 或 'nan' 的文件夹）
    if not device_name:
        print(f"跳过第{idx}行：设备名称为空或无效（原值: {repr(raw_name)})")
        continue

    # 把设备名中的不合法文件名字符替换为下划线，以免 Windows 报错
    device_name_safe = re.sub(r'[\\/:*?"<>|]', '_', device_name)

    device_folder = os.path.join(output_dir, device_name_safe)
    os.makedirs(device_folder, exist_ok=True)

    # 1) 处理两个 .cfg（支持多个字段替换）
    for cfg_file in ['imageDataCollecter.cfg', 'imageDataCommonCollecter.cfg']:
        src = os.path.join(template_dir, cfg_file)
        dst = os.path.join(device_folder, cfg_file)
        if not os.path.exists(src):
            print(f"模板缺失：{src}（跳过）")
            continue

        # 构建字段映射（cfg字段 -> csv列标题对应的值）
        cfg_field_map = {
            'stationName=': safe_str(row.get('设备编码', '').strip()),
            'seriesDescription=': safe_str(row.get('诊疗项目编码', '').strip()),
            'localAreaTag=': safe_str(global_row.get('Hospital Code', '').strip()),
            'ftpServerHost=': global_row.get('FTP Address', '').strip(),
            'pacsDbConnectUrl=': global_row.get('Database URL', '').strip(),
            'pacsDbPasswd=': global_row.get('Database PWD', '').strip(),
            'apiAhisAreaTag=': safe_str(global_row.get('AHIS Code', '').strip()),
            'apiAppKey=': global_row.get('AHIS AppKey', '').strip(),
            'apiAppSecret=': global_row.get('AHIS PWD', '').strip()
        }

        # ⭐ 特殊设备定制（仅对 imageDataCollecter.cfg 生效）
        if cfg_file == 'imageDataCollecter.cfg' and device_code == '10302501':
            special_map = {
                'exportedImageFilePath=': r'D:\\Optos Data\\Images\\Secondary',
                'exportedFileSeparatorStrs=': '-',
                'exportedFilePartIndexStrs=': '0',
                'fileSeparatorStrsForPart=': '-',
                'filePartIndexStrsForPart=': '2',
                'osEyeTags=': '-L',
                'odEyeTags=': '-R'
            }

            # 覆盖写入
            cfg_field_map.update(special_map)

        with open(src, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            leading_ws_len = len(line) - len(line.lstrip('\r\n\t '))
            leading = line[:leading_ws_len]
            stripped = line.lstrip()

            replaced = False
            for key, value in cfg_field_map.items():
                if stripped.startswith(key):
                    new_lines.append(f"{leading}{key}{value}\n")
                    replaced = True
                    break

            if not replaced:
                new_lines.append(line)

        with open(dst, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    # 2) 处理 MTW.exe.config（使用 lxml 保留注释）
    xml_src = os.path.join(template_dir, 'MTW.exe.config')
    xml_dst = os.path.join(device_folder, 'MTW.exe.config')
    if os.path.exists(xml_src):
        try:
            parser = etree.XMLParser(remove_blank_text=False)
            tree = etree.parse(xml_src, parser)
            root = tree.getroot()
        except Exception as e:
            print(f"解析 XML 模板失败：{xml_src} -> {e}")
            continue

        # 兼容命名空间：查找所有名为 add 的元素
        add_nodes = root.xpath('.//*[local-name()="add"]')
        changed = False
        for node in add_nodes:
            key_val = node.get('key', '')
            if key_val == 'modality':
                node.set('value', device_code)
                changed = True
            elif key_val == 'items':
                node.set('value', project_code)
                changed = True

        # === 新增功能开始 ===
        remark = str(row.get('备注', '')).strip()
        if remark == "Common":
            for node in add_nodes:
                if node.get('key') == 'checkTimeout':
                    node.set('value', '25')
                    changed = True
        # === 新增功能结束 ===

        # === 新增功能：替换 <add key="url" ...> 中的 IP 地址（更稳健版） ===
        # 优先使用当前行的 FTP Address；若为空则使用 global_row 中的值（兼容你把 FTP 写在第一行的场景）
        ftp_addr = str(row.get('FTP Address', '') or global_row.get('FTP Address', '')).strip()

        if ftp_addr:
            # 找到所有 key="url" 的节点
            url_nodes = [n for n in add_nodes if n.get('key') == 'url']
            for node in url_nodes:
                old_val = node.get('value', '') or ''

                # 更稳健的正则：捕获协议、IP、可选端口与后续可能的路径
                # groups: 1=protocol (http:// or https://), 2=ip, 3=port (包括冒号，如 :8081) 或 None, 4=rest（如 /path）
                m = re.search(r'^(https?://)(\d{1,3}(?:\.\d{1,3}){3})(:\d+)?(.*)$', old_val)
                if m:
                    protocol = m.group(1)
                    port = m.group(3) or ''   # 可能为 None
                    rest = m.group(4) or ''
                    new_val = f"{protocol}{ftp_addr}{port}{rest}"

                    # 只在实际变化时修改并记录
                    if new_val != old_val:
                        node.set('value', new_val)
                        changed = True
                        print(f"替换 URL (设备 {device_name_safe})：{old_val}  ->  {new_val}")
                else:
                    # 如果没匹配到预期格式，也试一次更宽松的替换（找到第一个 IPv4 并替换）
                    new_val2 = re.sub(r'(\d{1,3}(?:\.\d{1,3}){3})', ftp_addr, old_val, count=1)
                    if new_val2 != old_val:
                        node.set('value', new_val2)
                        changed = True
                        print(f"宽松替换 URL (设备 {device_name_safe})：{old_val}  ->  {new_val2}")

        tmp_dst = xml_dst + '.tmp'
        tree.write(tmp_dst, encoding='utf-8', xml_declaration=True, pretty_print=True)
        os.replace(tmp_dst, xml_dst)

        # === 新增：替换 MTW.exe.config 中的 <S数字> 和 <SUB数字/> ===
        with open(xml_dst, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 匹配 <S12345678> / </S12345678> / <SUB12345678/>
        xml_content = re.sub(r'<S\d+>', f'<S{device_code}>', xml_content)
        xml_content = re.sub(r'</S\d+>', f'</S{device_code}>', xml_content)
        xml_content = re.sub(r'<SUB\d+/>', f'<SUB{device_code}/>', xml_content)

        with open(xml_dst, 'w', encoding='utf-8') as f:
            f.write(xml_content)

    else:
        print(f"模板缺失：{xml_src}（跳过）")

    print(f"已生成设备配置：{device_folder}")

print("全部完成。")
