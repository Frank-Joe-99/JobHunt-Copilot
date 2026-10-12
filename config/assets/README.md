# 🖼️ config/assets/ 目录：个人多媒体资源

> 本文件夹用于存放候选人个人的静态图像资源，主要供简历排版引擎编译 Word 与 PDF 简历时引用。本目录下的真实图片受 `.gitignore` 保护，不会被提交至代码仓库。

---

## 📁 规范文件名与推荐规格

| 推荐文件名 | 文件类型 | 建议规格与格式 | 用途说明 |
| :--- | :--- | :--- | :--- |
| `avatar.png` 或 `avatar.jpg` | 个人证件照 | 1:1 或 2寸比例，白底或蓝底，文件大小 ≤ 2MB | 现代风简历头部右侧照片展示 |
| `school_logo.png` | 毕业院校校徽 | 透明底 PNG 格式矢量图或高清图，长宽比 1:1 | 简历头部中间校徽标识展示 |

---

## 🛠️ 添加与关联图片操作 (Procedures)

### 1. 前置条件 (Prerequisites)
- 图片文件格式为 PNG 或 JPG/JPEG。
- 确认文件存放在 `config/assets/` 目录下。

---

### 2. 放置与关联步骤

#### 步骤 1：拷贝图片至资源目录
将证件照和校徽文件复制到当前目录：
- 证件照保存为：`config/assets/avatar.png`
- 校徽保存为：`config/assets/school_logo.png`

#### 步骤 2：在个人主档案中配置路径
打开 `config/profile.yaml`，在 `basics` 节点下声明相对路径：
```yaml
basics:
  name: "张三"
  avatar: "config/assets/avatar.png"
  school_logo: "config/assets/school_logo.png"
```

#### 步骤 3：验证图片引入效果
在终端执行简历编译命令：
```bash
uv run jobhunt resume
```
*预期结果*：
- 编译生成 `storage/resumes/resume_default.pdf` 与 `.docx`；
- 打开产物验证校徽与个人照片是否正常显示在简历顶部标题区域；
- 若未提供可选图片，系统将自动触发安全回退策略跳过图片板块，不中断简历编译。
