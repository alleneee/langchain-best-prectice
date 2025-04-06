"""
验证码生成和验证服务
"""

import io
import time
import uuid
import base64
from typing import Dict, Tuple, Optional
from PIL import Image
from captcha.image import ImageCaptcha

from app.core.logging import logger


class CaptchaService:
    """验证码服务类"""
    
    def __init__(self, expiration_time: int = 300):
        """
        初始化验证码服务
        
        参数:
            expiration_time: 验证码过期时间(秒)，默认5分钟
        """
        self._captchas: Dict[str, Dict] = {}  # 存储验证码{id: {text, timestamp}}
        self.expiration_time = expiration_time
        self.image_generator = ImageCaptcha(width=160, height=60)
        logger.info(f"验证码服务初始化，过期时间: {self.expiration_time}秒")
    
    def generate_captcha(self) -> Tuple[Image.Image, str]:
        """
        生成新的验证码
        
        返回:
            (验证码图像对象, 验证码ID)
        """
        # 生成随机文本
        import random
        import string
        captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        # 生成验证码图像
        captcha_bytes = self.image_generator.generate(captcha_text)
        captcha_image = Image.open(io.BytesIO(captcha_bytes.getvalue()))
        
        # 存储验证码
        captcha_id = str(uuid.uuid4())
        self._captchas[captcha_id] = {
            'text': captcha_text,
            'timestamp': time.time()
        }
        
        logger.debug(f"生成新的验证码: ID={captcha_id}, 文本={captcha_text}")
        return captcha_image, captcha_id
    
    def verify_captcha(self, captcha_id: str, user_input: str) -> bool:
        """
        验证用户输入的验证码
        
        参数:
            captcha_id: 验证码ID
            user_input: 用户输入的验证码文本
            
        返回:
            验证是否成功
        """
        if not captcha_id or not user_input:
            logger.warning("验证码ID或用户输入为空")
            return False
        
        # 检查验证码是否存在
        if captcha_id not in self._captchas:
            logger.warning(f"验证码ID不存在: {captcha_id}")
            return False
        
        captcha_data = self._captchas[captcha_id]
        stored_text = captcha_data['text']
        
        # 验证并移除验证码(不区分大小写)
        is_valid = user_input.upper() == stored_text.upper()
        
        if is_valid:
            logger.debug(f"验证码验证成功: ID={captcha_id}")
            del self._captchas[captcha_id]
        else:
            logger.warning(f"验证码验证失败: ID={captcha_id}, 预期={stored_text}, 实际={user_input}")
        
        return is_valid
    
    def clean_expired_captchas(self) -> int:
        """
        清理过期的验证码
        
        返回:
            清理的验证码数量
        """
        current_time = time.time()
        expired_ids = [
            captcha_id for captcha_id, data in self._captchas.items()
            if current_time - data['timestamp'] > self.expiration_time
        ]
        
        for captcha_id in expired_ids:
            del self._captchas[captcha_id]
        
        if expired_ids:
            logger.info(f"清理了 {len(expired_ids)} 个过期验证码")
        
        return len(expired_ids)
    
    def get_captcha_as_base64(self, captcha_id: str) -> Optional[str]:
        """
        根据ID获取验证码的base64编码图像
        
        参数:
            captcha_id: 验证码ID
            
        返回:
            base64编码的图像字符串，如果验证码不存在则返回None
        """
        if captcha_id not in self._captchas:
            logger.warning(f"尝试获取不存在的验证码: {captcha_id}")
            return None
        
        # 重新生成验证码图像
        captcha_text = self._captchas[captcha_id]['text']
        captcha_bytes = self.image_generator.generate(captcha_text)
        
        # 转换为base64
        base64_image = base64.b64encode(captcha_bytes.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{base64_image}" 