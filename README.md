# 📚 二手图书交易平台（Second-hand Bookstore）

一个基于 **Python + Flask + SQLite** 的二手图书交易平台，实现了从用户注册、卖家认证、图书发布、**AI 图书成色评估**、搜索浏览、交易下单到模拟支付、订单管理的完整闭环，并内置**混合推荐系统**与**管理后台数据看板**。

> 毕业设计级完整项目，代码模块化、注释齐全，适合作为 Web 全栈 / Python 后端的求职展示项目。

---

## ✨ 功能特性

### 👤 用户模块
- 用户注册（买家 / 卖家）、登录（记住我）、登出
- 卖家实名认证（姓名、身份证、电话）与管理员审核
- 密码使用 Werkzeug 哈希加密存储

### 📖 书籍模块
- 卖家发布书籍：封面 / 扉页 / 内页 / 封底 四类照片上传
- **AI 自动成色评估**（阿里云通义千问 `qwen-vl-max` 多模态，可降级为用户自评）
- 多条件搜索（书名 / 作者 / ISBN）+ 价格区间 + 新旧程度筛选，分页展示
- 书籍详情、本人编辑 / 下架 / 库存管理

### 🤝 交易模块
- 买家发起购买请求（可留言），卖家同意 / 拒绝并回复
- 同意后自动拒绝同书其他待处理请求，避免冲突
- 买家模拟付款 → 扣减库存 / 标记售出
- 书籍交换（易物）意向功能

### 🎯 推荐系统（混合推荐）
- **基于内容的推荐**：作者 / 出版社 / 标题词重叠（Jaccard）/ 价格相似度
- **协同过滤**：买过同一本书的其他用户的行为
- **热门补足**：按购买次数推荐，保证结果不为空

### 📊 管理后台
- ECharts 数据看板：书籍 / 用户 / 订单统计、价格分布、近 6 个月交易与注册趋势、畅销书 / 活跃卖家买家、本周新增等
- 书籍管理、用户管理（卖家认证审核）、订单管理

### 🤖 AI 选书助手
- 按课程关键词快速检索相关二手书

---

## 🛠 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | Flask 2.3.3（应用工厂 + 蓝图） |
| 数据库 / ORM | SQLite + Flask-SQLAlchemy 3.0.5 |
| 用户认证 | Flask-Login 0.6.2 + Werkzeug 密码哈希 |
| AI 能力 | 阿里云通义千问 `qwen-vl-max`（`dashscope` SDK） |
| 前端 | HTML5 + CSS3（响应式）+ 原生 JavaScript + ECharts |
| 环境 | Python 3.10+ |

---

## 🏗 系统架构

```
浏览器 (HTML/CSS/JS + ECharts)
        │ HTTP
        ▼
Flask 应用工厂 create_app()
        │
  注册 6 个蓝图（Blueprint）
        │
  ├─ main.py          首页 / 最新上架
  ├─ auth.py          注册 / 登录 / 登出
  ├─ books.py         发布 / 浏览 / 搜索 / 编辑 / AI评估 / AI选书
  ├─ transactions.py  购买 / 同意 / 拒绝 / 付款 / 交换
  ├─ user.py          买家中心 / 卖家中心 / 库存 / 卖家申请
  └─ admin.py         数据看板 / 书籍 / 用户 / 订单管理
        │
   ┌────┴───────────┐
   │ models.py      │  SQLAlchemy ORM (User / Book / Transaction)
   │ recommendation.py │ 混合推荐算法
   │ apikey.py      │  阿里云千问多模态成色评估
   └────────────────┘
        │
      SQLite (bookstore.db)
```

### 数据库表设计

- **users**：用户 / 买家 / 卖家 / 管理员，含卖家实名认证信息
- **books**：书籍信息、状态（在售 / 已售 / 下架）、新旧程度、四类照片路径、AI 评估结果、库存、价格
- **transactions**：购买请求、状态机（待处理 → 已同意 → 已付款 / 已拒绝 / 已完成）、留言与卖家回复

---

## 🚀 快速开始

### 1. 克隆 & 安装依赖

```bash
git clone <your-repo-url>
cd second-hand-bookstore
pip install -r requirements.txt
```

### 2. 初始化数据库（自动创建表 + 测试数据）

```bash
python init_db.py
```

### 3. 启动应用

```bash
python app.py
# Windows 也可双击「启动.bat」
```

浏览器访问 **http://localhost:5000**

### 4. 测试账号

| 类型 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 买家 | buyer1 | 123456 |
| 卖家 | seller1 | 123456 |
| 卖家 | seller2 | 123456 |

---

## 🤖 AI 成色评估配置（可选）

发布书籍时会自动调用通义千问视觉模型评估书籍成色；**未配置 API Key 时自动降级为用户自评**，不影响使用。

```bash
# Windows PowerShell
$env:QWEN_API_KEY="your-api-key"

# Linux / macOS
export QWEN_API_KEY="your-api-key"
```

API Key 获取：[阿里云百炼平台](https://dashscope.console.aliyun.com/)（开通「百炼」→ API 密钥管理）。

> ⚠️ 请务必通过环境变量注入 Key，**不要**把真实 Key 写进 `config.py`。

---

## 📁 项目结构

```
second-hand-bookstore/
├── app.py                  # 应用入口（工厂 + 蓝图注册）
├── config.py               # 配置（密钥 / 数据库 / 上传 / 分页）
├── models.py               # SQLAlchemy 模型（User / Book / Transaction）
├── auth.py                 # 用户认证蓝图
├── books.py                # 书籍管理蓝图（含 AI 评估、AI 选书）
├── transactions.py         # 交易处理蓝图
├── user.py                 # 个人中心蓝图
├── admin.py                # 管理后台蓝图（含数据看板）
├── recommendation.py       # 混合推荐算法
├── apikey.py               # 千问多模态成色评估封装
├── init_db.py              # 数据库初始化（含测试数据）
├── migrate_schema.py       # 数据库迁移脚本
├── clear_test_data.py      # 清空测试数据
├── requirements.txt        # 依赖清单
├── .env.example            # 环境变量示例
├── templates/              # Jinja2 模板（按蓝图分目录）
├── static/
│   ├── css/style.css       # 全局样式
│   └── js/echarts.min.js   # 看板图表库
└── 启动.bat                # Windows 快速启动
```

---

## 🗺 后续可扩展方向

- [ ] 用户评价 / 站内消息系统
- [ ] 接入真实支付（支付宝 / 微信）
- [ ] 图片压缩与对象存储（OSS / COS）
- [ ] RESTful API 与前后端分离（Vue / React）
- [ ] 全文搜索（Elasticsearch / 向量检索）
- [ ] 部署上线（Nginx + Gunicorn + 云数据库）

---

## 📄 License

MIT License。本项目仅供学习交流与求职展示使用。
