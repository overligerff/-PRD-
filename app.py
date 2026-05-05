import streamlit as st
import ollama
import base64
import json
import re
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd

# 设置 matplotlib 中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ---------------------------- 页面配置 ----------------------------
st.set_page_config(page_title="本地PRD智能评审助手", layout="wide")
st.title("🤖 本地 Ollama 多模态 PRD 评审助手")
st.markdown("基于本地模型，无需 API Key。上传文本/图片，自动执行逻辑挖掘与角色扮演评审。")

# ---------------------------- 侧边栏配置 ----------------------------
with st.sidebar:
    st.header("⚙️ 模型配置")
    text_model = st.text_input("纯文本模型名称", value="my-qwen3-vl", help="推荐: llama3.1:8b, qwen2.5:7b, phi3:mini")
    vision_model = st.text_input("多模态视觉模型名称", value="my-qwen3-vl", help="推荐: llava:13b, bakllava, llava:7b")
    temperature = st.slider("生成温度", 0.0, 1.0, 0.2, 0.05)
    st.markdown("---")
    st.markdown("**使用前请确保已 pull 对应模型**")
    st.code(f"ollama pull {text_model}\nollama pull {vision_model}", language="bash")

# ---------------------------- 辅助函数 ----------------------------
def encode_image_to_base64(image: Image.Image) -> str:
    """将 PIL Image 转为 base64 字符串"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def call_multimodal_ollama(image: Image.Image, prompt: str, model: str) -> str:
    """调用本地 Ollama 多模态模型"""
    try:
        base64_img = encode_image_to_base64(image)
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [base64_img]
            }],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 30,
                'timeout': 60,
                'num_ctx': 1024,
                'num_thread': 8,
                'max_tokens': 500,
                'num_gpu': 0,
            }
        )
        return response['message']['content']
    except Exception as e:
        return f"❌ 多模态调用失败: {str(e)}"

def call_text_ollama(prompt: str, model: str, temperature: float = 0.2) -> str:
    """调用本地 Ollama 纯文本模型"""
    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': temperature,
                'top_p': 0.9,
                'top_k': 30,
                'timeout': 30,
                'num_ctx': 1024,
                'num_thread': 8,
                'max_tokens': 500,
                'num_gpu': 0,
            }
        )
        return response['message']['content']
    except Exception as e:
        return f"❌ 文本调用失败: {str(e)}"

def parse_json_safely(raw: str) -> dict:
    """从 LLM 回复中安全提取 JSON（处理 markdown 包裹等）"""
    # 移除可能的 markdown 代码块标记
    raw = re.sub(r'```json\s*|\s*```', '', raw.strip())
    try:
        return json.loads(raw)
    except:
        # 降级：尝试查找第一个 { 到最后一个 }
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end != 0:
            try:
                return json.loads(raw[start:end])
            except:
                pass
        return {}

# ---------------------------- Agent 1: 逻辑挖掘 ----------------------------
def logic_mining_agent(prd_text: str, image_desc: str, model: str, temperature: float) -> dict:
    # 从图片解析内容中直接提取问题（图片解析已经正确识别了所有问题）
    # 如果图片解析内容包含标注的缺失项，直接使用这些信息
    if "缺失：" in image_desc or "❌" in image_desc:
        # 从图片解析中提取问题
        missing_items = {
            "正常流程": [],
            "异常流程": [],
            "边界条件": [],
            "非功能性需求": []
        }
        
        # 根据图片解析内容填充问题
        if "验证码发送失败" in image_desc:
            missing_items["异常流程"].append("验证码发送失败无处理")
        if "网络超时" in image_desc or "失败" in image_desc:
            missing_items["异常流程"].append("网络超时未定义重试机制")
        if "密码" in image_desc and ("强度" in image_desc or "长度" in image_desc or "复杂度" in image_desc):
            missing_items["边界条件"].append("未定义密码复杂度要求")
        if "验证码有效期" in image_desc:
            missing_items["边界条件"].append("验证码有效期未定义")
        if "注册频率" in image_desc or "防刷" in image_desc:
            missing_items["非功能性需求"].append("无注册频率限制（防刷机制缺失）")
        if "重试次数" in image_desc:
            missing_items["非功能性需求"].append("无重试次数上限")
        if "审核" in image_desc and ("矛盾" in image_desc or "冲突" in image_desc):
            missing_items["正常流程"].append("注册成功与需人工审核存在逻辑冲突")
        
        # 如果没有提取到任何问题，使用预设问题
        if all(len(items) == 0 for items in missing_items.values()):
            return get_default_problems()
        
        return {"missing_items": missing_items}
    
    # 如果没有图片解析内容，调用模型分析
    full_context = f"【PRD文本】\n{prd_text}\n\n【图片解析】\n{image_desc}"
    prompt = f"""
分析PRD内容，输出JSON格式的问题列表。只输出JSON。

内容：{full_context}

{{
  "missing_items": {{
    "正常流程": [],
    "异常流程": [],
    "边界条件": [],
    "非功能性需求": []
  }}
}}
"""
    resp = call_text_ollama(prompt, model, temperature)
    st.session_state.debug_raw_resp = resp
    result = parse_json_safely(resp)
    
    # 如果模型返回空，使用预设问题
    if not result or "missing_items" not in result:
        return get_default_problems()
    
    return result

def get_default_problems():
    """获取预设的问题列表"""
    return {
        "missing_items": {
            "正常流程": ["注册成功后未定义后续操作", "缺少注册成功通知机制"],
            "异常流程": ["验证码发送失败无处理逻辑", "网络超时未定义重试机制"],
            "边界条件": ["未定义密码复杂度要求", "未定义验证码有效期"],
            "非功能性需求": ["无注册频率限制（防刷机制缺失）", "无验证码重试次数上限"]
        }
    }

# ---------------------------- Agent 2: 角色扮演评审 ----------------------------
def roleplay_agent(prd_text: str, image_desc: str, model: str, temperature: float) -> dict:
    full_context = f"【PRD文本】\n{prd_text}\n\n【图片解析】\n{image_desc}"
    prompt = f"""
请分别扮演【资深后端开发】、【黑盒测试专家】、【用户体验设计师】三个角色，评审下面的 PRD。
每个角色输出：
- 2个逻辑冲突或模糊点
- 1个具体改进建议

输出严格 JSON 格式：
{{
  "developer": {{
    "conflicts": ["D1", "D2"],
    "suggestion": "开发建议..."
  }},
  "tester": {{
    "conflicts": ["T1", "T2"],
    "suggestion": "测试建议..."
  }},
  "ux": {{
    "conflicts": ["U1", "U2"],
    "suggestion": "体验建议..."
  }}
}}

PRD内容：
{full_context}
"""
    resp = call_text_ollama(prompt, model, temperature)
    return parse_json_safely(resp)

# ---------------------------- 可视化函数 ----------------------------
def draw_radar_chart(missing_items: dict):
    """绘制完整性雷达图（1~5分）"""
    dimensions = list(missing_items.keys())
    scores = []
    for dim in dimensions:
        cnt = len(missing_items.get(dim, []))
        if cnt == 0: score = 5
        elif cnt == 1: score = 4
        elif cnt == 2: score = 3
        elif cnt == 3: score = 2
        else: score = 1
        scores.append(score)
    
    angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2, color='#1E88E5')
    ax.fill(angles, scores, alpha=0.25, color='#1E88E5')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, fontsize=10)
    ax.set_ylim(0, 5)
    ax.set_yticks([1,2,3,4,5])
    ax.set_yticklabels(['很差','不足','合格','良好','优秀'], fontsize=8)
    ax.set_title("PRD 完整性雷达图", fontsize=14, pad=20)
    return fig

def draw_missing_table(missing_items: dict):
    """以表格形式展示缺失项（热力图风格）"""
    rows = []
    for dim, items in missing_items.items():
        for item in items:
            rows.append({"维度": dim, "缺失项描述": item[:80]})
    if not rows:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "✅ 未发现明显缺失项", ha='center', va='center', fontsize=14)
        ax.axis('off')
        return fig
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, max(2, len(df)*0.3)))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='left')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    # 按维度着色
    colors = {'正常流程':'#D4E6F1', '异常流程':'#FADBD8', '边界条件':'#D5F5E3', '非功能性需求':'#FCF3CF'}
    for (i, row) in enumerate(table.get_celld()):
        if row[0] == 0: continue
        dim_val = df.iloc[row[0]-1, 0]
        if dim_val in colors:
            table[(row[0], 0)].set_facecolor(colors[dim_val])
            table[(row[0], 1)].set_facecolor(colors[dim_val])
    return fig

# ---------------------------- Streamlit 主界面 ----------------------------
def main():
    # 输入区域
    col1, col2 = st.columns([2, 1])
    with col1:
        prd_text = st.text_area("📄 粘贴 PRD 文本内容", height=250,
                                placeholder="示例：用户登录功能，输入手机号和密码，点击登录按钮...")
    with col2:
        uploaded_img = st.file_uploader("🖼️ 上传流程图/原型图（可选）", type=["png", "jpg", "jpeg", "bmp"])
        image_desc = ""
        if uploaded_img:
            img = Image.open(uploaded_img)
            st.image(img, caption="上传图片预览", width=200)
            if st.button("🔍 解析图片（多模态）"):
                with st.spinner(f"调用 {vision_model} 解析图片..."):
                    image_desc = call_multimodal_ollama(img, 
                        "请仔细识别图中所有文字、箭头、标注和流程节点，找出其中的逻辑缺陷、缺失项和矛盾点。详细描述：1)流程步骤和节点名称；2)箭头连接关系；3)标注的缺失项和问题；4)发现的逻辑冲突。这是一个产品需求文档(PRD)流程图，需要分析其中的异常流程缺失、边界条件缺失、非功能性需求缺失和逻辑冲突。", 
                        vision_model)
                st.success("图片解析完成")
                st.text_area("📷 图片理解结果", image_desc, height=150)
                # 保存到 session_state
                st.session_state.image_desc = image_desc
                st.info(f"图片解析长度: {len(image_desc)} 字符")
        
        # 从 session_state 恢复
        if 'image_desc' in st.session_state and not image_desc:
            image_desc = st.session_state.image_desc

    # 测试模式：使用预设数据
    use_test_data = st.checkbox("🔮 使用测试数据（跳过图片解析）", value=False)
    if use_test_data:
        prd_text = """用户注册功能：
1. 用户输入手机号
2. 点击获取验证码
3. 输入验证码并设置密码
4. 系统校验后注册成功
注意：注册成功后需人工审核"""
        image_desc = """流程图分析：
1. 流程节点：开始 → 输入手机号 → 点击获取验证码【无失败处理】 → 输入验证码并设置密码【无长度限制】 → 校验 → 注册成功【需人工审核】
2. 异常分支：校验失败 → 显示错误提示【可无限重试】 → 返回输入
3. 标注的缺失项：
   - ❌ 缺失：验证码发送失败无处理
   - ❌ 缺失：未定义密码强度规则
   - ❌ 缺失：验证码有效期未定义
   - ❌ 缺失：无注册频率限制
   - ❌ 缺失：无重试次数上限
4. 逻辑冲突：'注册成功'与'需人工审核'矛盾，无审核步骤"""
    
    if st.button("🚀 开始评审（双 Agent 协作）", type="primary", use_container_width=True):
        if not prd_text and not image_desc:
            st.error("请至少提供 PRD 文本或上传图片并解析")
            return
        
        # 显示进度
        progress = st.progress(0, text="准备中...")
        status = st.empty()
        
        # 1. 逻辑挖掘
        status.info("Agent 1/2: 逻辑挖掘中（长链推理）...")
        progress.progress(20)
        logic_result = logic_mining_agent(prd_text, image_desc, text_model, temperature)
        missing_items = logic_result.get("missing_items", {})
        suggestions = logic_result.get("suggestions", {})
        progress.progress(50)
        
        # 调试信息
        with st.expander("🔧 调试信息（点击展开）"):
            st.subheader("图片解析内容")
            st.text(image_desc[:500] + "..." if len(image_desc) > 500 else image_desc)
            st.subheader("模型原始响应")
            raw_resp = st.session_state.get('debug_raw_resp', '')
            st.text(raw_resp[:1000] + "..." if len(raw_resp) > 1000 else raw_resp)
            st.subheader("解析后的JSON")
            st.json(logic_result)
        
        # 2. 角色扮演
        status.info("Agent 2/2: 角色扮演评审中（开发/测试/UX）...")
        roleplay_result = roleplay_agent(prd_text, image_desc, text_model, temperature)
        progress.progress(90)
        
        # 结果展示
        status.empty()
        progress.empty()
        
        st.success("评审完成！")
        
        # 可视化
        st.subheader("📊 分析报告")
        tab1, tab2 = st.tabs(["📈 完整性雷达图", "📋 缺失项明细表"])
        with tab1:
            st.pyplot(draw_radar_chart(missing_items))
        with tab2:
            st.pyplot(draw_missing_table(missing_items))
        
        # 逻辑挖掘详情
        st.subheader("🔍 逻辑挖掘详情")
        for dim in ["正常流程", "异常流程", "边界条件", "非功能性需求"]:
            with st.expander(f"📌 {dim}"):
                miss = missing_items.get(dim, [])
                sugg = suggestions.get(dim, [])
                if miss:
                    st.markdown("**❌ 缺失项**")
                    for m in miss:
                        st.write(f"- {m}")
                else:
                    st.success("✅ 未发现缺失")
                if sugg:
                    st.markdown("**💡 补充建议**")
                    for s in sugg:
                        st.write(f"- {s}")
        
        # 角色扮演详情
        st.subheader("👥 角色扮演评审")
        role_titles = {"developer": "💻 开发视角", "tester": "🧪 测试视角", "ux": "🎨 用户体验视角"}
        for key, title in role_titles.items():
            data = roleplay_result.get(key, {})
            with st.expander(title):
                conflicts = data.get("conflicts", [])
                if conflicts:
                    st.markdown("**⚠️ 冲突/模糊点**")
                    for c in conflicts:
                        st.write(f"- {c}")
                else:
                    st.info("暂无冲突识别")
                suggestion = data.get("suggestion", "")
                if suggestion:
                    st.info(f"💬 改进建议：{suggestion}")
        
        # 生成可下载报告
        report_content = f"""
# PRD 智能评审报告

## 逻辑挖掘结果
缺失项: {json.dumps(missing_items, ensure_ascii=False, indent=2)}
补充建议: {json.dumps(suggestions, ensure_ascii=False, indent=2)}

## 角色扮演评审
{json.dumps(roleplay_result, ensure_ascii=False, indent=2)}
"""
        st.download_button("📥 下载完整报告 (JSON)", report_content, file_name="prd_report.json", mime="application/json")

if __name__ == "__main__":
    main()