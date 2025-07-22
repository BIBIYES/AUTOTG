#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    """配置管理类"""
    
    def __init__(self, config_file='config.json'):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为'config.json'
        """
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"已成功加载配置文件: {self.config_file}")
            else:
                logger.warning(f"配置文件不存在: {self.config_file}")
                self.config = {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = {}
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            logger.info(f"已成功保存配置文件: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """
        获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值，如果配置项不存在则返回该值
            
        Returns:
            配置项值
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
            
        Returns:
            成功返回True，失败返回False
        """
        self.config[key] = value
        return self.save_config()
    
    def remove(self, key):
        """
        删除配置项
        
        Args:
            key: 配置项键名
            
        Returns:
            成功返回True，失败返回False
        """
        if key in self.config:
            del self.config[key]
            return self.save_config()
        return True 