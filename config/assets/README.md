# 简历图片

存放可选证件照与校徽，供本地 Word / PDF 排版使用。

| 文件示例 | 档案字段 |
| --- | --- |
| `config/assets/avatar.png` | `basics.avatar` |
| `config/assets/school_logo.png` | `basics.school_logo` |

将下面片段合并到已有 `basics`，其他必填字段见[档案模板](../profile.example.yaml)：

```yaml
basics:
  avatar: "config/assets/avatar.png"
  school_logo: "config/assets/school_logo.png"
```

使用项目内相对路径及 PNG / JPG 图片；不需要图片时留空。缺失的可选图片会跳过。

运行 `uv run jobhunt resume` 后检查生成物的图片与分页。真实图片不提交；本 README、占位文件和明确公开样例可受版本控制。
