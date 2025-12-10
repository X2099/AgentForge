#!/usr/bin/env python3
import re

with open('src/webui/chat_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 使用正则表达式替换样式块
pattern = r'    # ChatGPT风格的样式定义\s+st\.markdown\(\s*"""\s*<style>.*?</style>\s*"""\s*,\s*unsafe_allow_html=True\)'

replacement = '''    # 极简样式
    st.markdown("""
    <style>
    /* 简洁布局 */
    .stTitle {
        margin-bottom: 10px !important;
    }

    .stCaption {
        margin-bottom: 15px !important;
        color: #666 !important;
    }

    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('src/webui/chat_ui.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('✅ 样式已简化')
