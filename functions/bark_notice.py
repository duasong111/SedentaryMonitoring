import requests
import urllib.parse
from http import HTTPStatus
from Common.Response import create_response
from config import BARK_DEVICE_KEY


class BarkNoticeFunction:
    def __init__(self):
        self.base_url = "https://api.day.app"
        self.device_key = BARK_DEVICE_KEY
    
    def _send_request(self, url):
        """发送HTTP请求"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return {"success": True, "message": "推送成功"}
        except Exception as e:
            return {"success": False, "message": f"推送失败: {str(e)}"}
    
    def send_notification(self, title, body, icon=None):
        """发送带标题和内容的通知
        
        Args:
            title: 推送标题
            body: 推送内容
            icon: 推送图标URL（可选）
            
        Returns:
            dict: 推送结果
        """
        if not self.device_key:
            return {"success": False, "message": "BARK_DEVICE_KEY未配置"}
        
        if not title or not body:
            return {"success": False, "message": "标题和内容不能为空"}
        
        # 编码URL参数
        encoded_title = urllib.parse.quote(title)
        encoded_body = urllib.parse.quote(body)
        
        # 构建URL
        url = f"{self.base_url}/{self.device_key}/{encoded_title}/{encoded_body}"
        
        # 添加图标参数
        if icon:
            encoded_icon = urllib.parse.quote(icon)
            url += f"?icon={encoded_icon}"
        
        return self._send_request(url)
    
    def send_simple_notification(self, content):
        """发送简单通知（只有内容，没有标题）
        
        Args:
            content: 推送内容
            
        Returns:
            dict: 推送结果
        """
        if not self.device_key:
            return {"success": False, "message": "BARK_DEVICE_KEY未配置"}
        
        if not content:
            return {"success": False, "message": "内容不能为空"}
        
        # 编码URL参数
        encoded_content = urllib.parse.quote(content)
        
        # 构建URL
        url = f"{self.base_url}/{self.device_key}/{encoded_content}"
        
        return self._send_request(url)
    
    def send_notification_with_icon(self, title, body, icon):
        """发送带图标通知
        
        Args:
            title: 推送标题
            body: 推送内容
            icon: 推送图标URL
            
        Returns:
            dict: 推送结果
        """
        return self.send_notification(title, body, icon)


# 全局实例
bark_notice = BarkNoticeFunction()