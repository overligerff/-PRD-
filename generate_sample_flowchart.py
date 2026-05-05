import matplotlib.pyplot as plt
import matplotlib
import matplotlib.patches as patches

# 设置 matplotlib 中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'sans-serif'

def draw_problematic_flowchart():
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.axis('off')
    
    # 绘制节点（增大尺寸和字体）
    def draw_box(x, y, text, color='lightblue', width=2.8, height=1.1):
        rect = patches.FancyBboxPatch((x - width/2, y - height/2), width, height,
                                      boxstyle="round,pad=0.1",
                                      facecolor=color, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=11, weight='bold')
    
    # 绘制红框警告区域
    def draw_warning_box(x, y, width, height):
        rect = patches.Rectangle((x - width/2, y - height/2), width, height,
                                 fill=False, edgecolor='red', linewidth=3, linestyle='dashed')
        ax.add_patch(rect)
    
    # 主流程节点
    draw_box(7, 10, "开始", color='lightgreen')
    draw_box(7, 8.2, "输入手机号", color='lightyellow')
    
    # 获取验证码节点 - 标注问题
    draw_box(7, 6.4, "点击获取验证码\n【无失败处理】", color='lightyellow')
    draw_warning_box(7, 6.4, 3.2, 1.3)  # 红框标注
    
    draw_box(7, 4.6, "输入验证码\n并设置密码\n【无长度限制】", color='lightyellow')
    draw_warning_box(7, 4.6, 3.2, 1.3)  # 红框标注
    
    draw_box(4, 2.8, "校验验证码\n和密码格式", color='lightcoral')
    draw_box(7, 1, "注册成功\n【需人工审核】", color='lightgreen')
    
    # 异常分支节点（有问题：没有重试上限）
    draw_box(10, 2.8, "显示错误提示\n【可无限重试】", color='lightgray')
    draw_warning_box(10, 2.8, 3.2, 1.3)  # 红框标注
    
    # 辅助标注：冲突点（放大字体）
    ax.text(7, 0.3, "❌ 逻辑冲突：'注册成功'与'需人工审核'矛盾，无审核步骤",
            ha='center', fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', linewidth=2, boxstyle='round,pad=0.4'))
    
    # 标注缺失项（更靠近节点，增大字体）
    # 验证码发送失败
    ax.text(11.5, 6.4, "⚠️ 缺失：验证码发送失败无处理", fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
    
    # 密码复杂度
    ax.text(1.5, 4.6, "⚠️ 缺失：未定义密码强度规则", fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
    
    # 验证码有效期
    ax.text(11.5, 4.6, "⚠️ 缺失：验证码有效期未定义", fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
    
    # 防刷机制
    ax.text(1.5, 8.2, "⚠️ 缺失：无注册频率限制", fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
    
    # 重试次数限制
    ax.text(1.5, 2.8, "⚠️ 缺失：无重试次数上限", fontsize=10, color='red', weight='bold',
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
    
    # 箭头（加粗）
    def arrow(start, end, color='gray', style='->'):
        ax.annotate("", xy=end, xytext=start,
                    arrowprops=dict(arrowstyle=style, lw=2, color=color))
    
    arrow((7, 9.5), (7, 8.7))
    arrow((7, 7.7), (7, 6.9))
    arrow((7, 5.9), (7, 5.1))
    arrow((7, 4.1), (4, 3.3))
    
    # 校验成功 → 注册成功
    arrow((4, 2.3), (7, 1.5), color='green')
    # 校验失败 → 错误重试
    ax.annotate("校验失败", xy=(9, 2.8), xytext=(5, 3.6), fontsize=9, color='red',
                arrowprops=dict(arrowstyle="->", lw=2, color='red', linestyle='dashed'))
    arrow((10, 2.3), (7, 4.1), color='red', style='->')
    
    # 冲突标注：从"注册成功"画一个虚线指向矛盾说明
    ax.annotate("❌矛盾", xy=(7, 0.8), xytext=(7, 1.5),
                arrowprops=dict(arrowstyle="->", lw=2, color='red', linestyle='dotted'))
    
    # 底部总结表格
    summary_table = [
        ["问题类型", "具体缺失"],
        ["异常流程", "验证码发送失败、网络超时"],
        ["边界条件", "密码复杂度、验证码有效期"],
        ["非功能性", "防刷机制、重试次数限制"],
        ["逻辑冲突", "注册成功与人工审核矛盾"]
    ]
    
    # 绘制表格
    table_ax = fig.add_subplot(111)
    table_ax.axis('off')
    table = table_ax.table(cellText=summary_table, colLabels=None, 
                          loc='bottom', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    plt.tight_layout()
    plt.savefig("problematic_prd_flowchart.png", dpi=200, bbox_inches='tight')
    plt.close()
    print("图片已生成：problematic_prd_flowchart.png (问题标注更明显)")

if __name__ == "__main__":
    draw_problematic_flowchart()
