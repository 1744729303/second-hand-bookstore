"""
阿里云百炼平台SDK调用模块
用于AI图书成色评估功能
使用dashscope官方SDK
"""

import base64
import json
import dashscope
from config import Config


def get_api_key():
    """
    获取API密钥
    优先从环境变量读取，其次从配置文件读取
    """
    import os
    
    # 优先使用环境变量
    api_key = os.environ.get('QWEN_API_KEY')
    
    # 如果环境变量没有，则从配置文件读取
    if not api_key:
        api_key = Config.QWEN_API_KEY
    
    if not api_key:
        raise ValueError("未找到千问API密钥，请设置环境变量 QWEN_API_KEY 或在config.py中配置")
    
    return api_key


def encode_image_to_base64(image_file):
    """
    将图片文件转换为base64编码
    
    参数:
        image_file: 图片文件对象（支持 FileStorage 或 BytesIO）
    
    返回:
        str: base64编码字符串
    """
    # 保存当前位置
    original_position = image_file.tell()
    
    # 读取图片数据
    image_file.seek(0)
    image_bytes = image_file.read()
    
    # 恢复到原位置
    image_file.seek(original_position)
    
    # 转换为base64
    base64_string = base64.b64encode(image_bytes).decode('utf-8')
    return base64_string


def assess_book_condition(cover_image, title_page_image, inside_images=None, back_cover_image=None):
    """
    使用千问大模型评估图书成色
    
    参数:
        cover_image: 封面图片文件对象（必需）
        title_page_image: 扉页图片文件对象（必需）
        inside_images: 内页图片文件对象列表（可选，最多3张）
        back_cover_image: 封底图片文件对象（可选）
    
    返回:
        dict: {
            'success': True/False,
            'condition': 'new|like_new|good|acceptable',
            'condition_text': '全新|几乎全新|良好|可接受',
            'reason': '评估理由',
            'confidence': 置信度 0-1
        }
        如果失败，返回包含 'success': False 和 'message' 的字典
    """
    try:
        # 设置API密钥
        api_key = get_api_key()
        dashscope.api_key = api_key
        
        # 将封面和扉页图片转换为base64
        cover_b64 = encode_image_to_base64(cover_image)
        title_b64 = encode_image_to_base64(title_page_image)
        
        # 构建消息内容 - dashscope格式
        content = []
        
        # 添加文本描述
        content.append({
            "text": """你是一位专业的二手图书成色评估专家。请根据提供的图书图片，评估图书的新旧程度。

评估标准：
- new（全新）：无任何使用痕迹，封面完好无损，内页洁白无标记
- like_new（几乎全新）：极其轻微的使用痕迹，几乎看不出使用过
- good（良好）：有轻微使用痕迹，如轻微折痕、少量笔记，但不影响阅读
- acceptable（可接受）：有明显使用痕迹，如磨损、折痕、较多笔记，但内容完整

请从以下维度分析：
1. 封面状况（磨损、折痕、污渍）
2. 书脊状况（裂痕、变形）
3. 内页状况（笔记、折痕、污渍、泛黄）
4. 整体保存状态

请以JSON格式返回评估结果，包含以下字段：
- condition: 成色等级（new/like_new/good/acceptable）
- condition_text: 成色中文描述
- reason: 详细评估理由（100字以内）
- confidence: 评估置信度（0.0-1.0）

只返回JSON，不要其他内容。"""
        })
        
        # 添加封面图片
        content.append({
            "image": f"data:image/jpeg;base64,{cover_b64}"
        })
        
        # 添加扉页图片
        content.append({
            "image": f"data:image/jpeg;base64,{title_b64}"
        })
        
        # 添加内页图片
        if inside_images:
            for img in inside_images[:3]:  # 最多处理3张内页
                img_b64 = encode_image_to_base64(img)
                content.append({
                    "image": f"data:image/jpeg;base64,{img_b64}"
                })
        
        # 添加封底图片
        if back_cover_image:
            back_b64 = encode_image_to_base64(back_cover_image)
            content.append({
                "image": f"data:image/jpeg;base64,{back_b64}"
            })
        
        # 调用千问VL模型 - dashscope官方格式
        from dashscope import MultiModalConversation
        response = MultiModalConversation.call(
            model='qwen-vl-max',
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        
        # 解析响应
        if response.status_code != 200:
            return {
                'success': False,
                'message': f"API调用失败: {response.code} - {response.message}"
            }
        
        # 获取响应内容
        result_text = response.output.choices[0]['message']['content'][0]['text']
        
        # 清理可能存在的markdown代码块
        result_text = result_text.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        # 尝试解析JSON
        result = json.loads(result_text)
        
        # 验证返回结果
        required_fields = ['condition', 'condition_text', 'reason', 'confidence']
        if not all(field in result for field in required_fields):
            return {
                'success': False,
                'message': 'API返回格式不正确，缺少必要字段'
            }
        
        # 确保condition在有效范围内
        valid_conditions = ['new', 'like_new', 'good', 'acceptable']
        if result['condition'] not in valid_conditions:
            return {
                'success': False,
                'message': f"API返回的成色等级无效: {result['condition']}"
            }
        
        # 确保置信度在有效范围内
        try:
            confidence = float(result['confidence'])
            confidence = max(0.0, min(1.0, confidence))  # 限制在0-1之间
            result['confidence'] = confidence
        except (ValueError, TypeError):
            result['confidence'] = 0.5  # 默认值
        
        result['success'] = True
        return result
        
    except ValueError as e:
        print(f"配置错误: {e}")
        return {
            'success': False,
            'message': f'配置错误: {str(e)}'
        }
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return {
            'success': False,
            'message': 'AI返回内容格式解析失败'
        }
    except Exception as e:
        print(f"千问API调用失败: {e}")
        return {
            'success': False,
            'message': f'AI评估服务暂时不可用: {str(e)}'
        }


def assess_book_condition_simple(cover_image, title_page_image):
    """
    简化版图书成色评估（仅使用封面和扉页）
    
    参数:
        cover_image: 封面图片文件对象
        title_page_image: 扉页图片文件对象
    
    返回:
        dict: 评估结果
    """
    return assess_book_condition(cover_image, title_page_image)


# 使用示例和测试
if __name__ == "__main__":
    print("=" * 50)
    print("千问大模型API模块 - 图书成色评估")
    print("=" * 50)
    print("\n配置说明:")
    print("1. 环境变量方式: set QWEN_API_KEY=your-api-key")
    print("2. 配置文件方式: 在 config.py 中设置 QWEN_API_KEY")
    print("\n安装SDK: pip install dashscope")
    print("\n使用示例:")
    print("  from apikey import assess_book_condition")
    print("  result = assess_book_condition(cover_img, title_img, inside_imgs, back_img)")
