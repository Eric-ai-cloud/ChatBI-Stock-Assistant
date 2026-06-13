# 🚀 ChatBI WebUI 快速启动指南

## ⏱️ 5分钟快速启动

### 第一步：检查环境（1分钟）

```bash
# 检查 Python 版本（需要 3.8+）
python --version

# 检查是否已安装 gradio
pip show gradio
```

### 第二步：设置 API Key（1分钟）

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="your-api-key-here"
```

**Linux/Mac:**
```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

> 💡 提示：如果没有 API Key，请访问 [DashScope 官网](https://dashscope.aliyun.com/) 申请

### 第三步：准备数据（1分钟）

```bash
# 复制数据库文件
cp ../CASE-ChatBI助手/stock_prices.db data/

# 创建图表目录
mkdir -p data/image_show
```

### 第四步：启动 WebUI（2分钟）

**方式一：使用启动脚本（推荐）**

Windows:
```bash
start_webui.bat
```

Linux/Mac:
```bash
chmod +x start_webui.sh
./start_webui.sh
```

**方式二：直接运行**
```bash
python webui.py
```

### 第五步：开始使用

浏览器会自动打开 **http://localhost:7860**

点击右侧的示例问题，或在输入框中输入您的问题！

---

## 💡 常见问题速查

### ❓ 启动时提示 "未设置 DASHSCOPE_API_KEY"

**解决方案：**
```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"

# Linux/Mac
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"
```

### ❓ 提示 "模块不存在" 或 "ImportError"

**解决方案：**
```bash
pip install -r requirements.txt
```

### ❓ 数据库文件不存在

**解决方案：**
```bash
# 从原项目复制
cp ../CASE-ChatBI助手/stock_prices.db data/
```

### ❓ 端口 7860 被占用

**解决方案：**
编辑 `webui.py`，修改端口：
```python
webui.run(server_port=8080)  # 改为其他端口
```

### ❓ 无法访问 http://localhost:7860

**解决方案：**
1. 检查防火墙设置
2. 尝试使用 127.0.0.1:7860
3. 查看控制台输出的实际地址

---

## 🎯 快速测试

启动成功后，尝试以下问题：

1. **基础查询**
   ```
   贵州茅台最近一个月的股价走势
   ```

2. **对比分析**
   ```
   对比五粮液和中芯国际2024年的涨跌幅
   ```

3. **预测功能**
   ```
   预测贵州茅台未来7天的股价
   ```

4. **技术分析**
   ```
   检测贵州茅台的布林带超买超卖点
   ```

---

## 📚 更多资源

- 📖 [完整使用指南](WEBUI_GUIDE.md)
- 🏗️ [架构说明](WEBUI_ARCHITECTURE.md)
- 📝 [项目 README](README.md)

---

## 🆘 获取帮助

如果遇到问题：

1. 查看控制台错误信息
2. 检查 [WEBUI_GUIDE.md](WEBUI_GUIDE.md) 的常见问题部分
3. 确认所有依赖已正确安装
4. 检查 API Key 是否有效

---

**祝您使用愉快！** 🎉
