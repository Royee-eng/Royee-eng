# 维护这份 GitHub 主页

主页仓库：`Royee-eng/Royee-eng`。根目录 `README.md` 是实际展示的主页。

## 内容与事实

- 个人简介来自本人确认：南安普顿大学软件工程大二、学习 Java 后端、目标 AI 应用与 Coding Agent / Agent Systems。
- 技术徽章是学习状态，不代表精通、工作经验或项目交付能力。
- 目前不展示项目卡片。以后只添加本人真实仓库，不用别人的项目填充。
- 不添加虚构贡献数、访客数、实习、获奖、旅行地点或摄影作品。
- `assets/hero.png` 是 AI 生成的氛围设计素材，并非本人拍摄。完整提示词见 `docs/ASSETS.md`。

## 加入一个真实项目

在 README 的 `PROJECTS` 注释后新增以下块，并删除原有的空状态文案。先检查链接可公开访问，且仓库属于自己；私有项目不自动公开。

```markdown
### [真实项目名称](https://github.com/Royee-eng/真实仓库名)

一句话说明它解决的实际问题。

**状态：** 实际状态 · **技术：** 实际使用的技术

[查看源码 →](https://github.com/Royee-eng/真实仓库名)
```

单列卡片式分节可以一直追加，手机端自然换行，不需要重做布局。不要使用展示在主页面中的虚构占位链接。

## 更新技术与成长路线

- 改 README 中的说明；只有本人确认后才改变学习状态。
- `scripts/build_art.py` 是等高线、路线、徽章和兴趣图标的源文件；运行它可重新生成相关素材，需要 Pillow。横幅由 imagegen 单独生成，不由此脚本重画。
- 若更换图片文件名，同步修改 README 的 `src` / `srcset`。
- 徒步路线动画只作装饰，不表示完成未来阶段；小屏幕和减少动态效果模式使用静态 SVG。
- Python 徽章对应此前确认的技术展示方向；如果不再学习，可直接删除该 `<img>`。

## 加入徒步与摄影

将自己的照片放到 `assets/field-notes/`，在 `FIELD NOTES` 注释之后加入图片和说明。只写实际去过的地点与日期，并保持照片体积适合移动网络；不要把 AI 横幅当作实拍作品。

## 贡献图自动更新

`.github/workflows/contributions.yml` 每天 06:17 UTC 请求 GitHub 官方 GraphQL API，并更新仓库内 `assets/contributions.svg`。也可在 Actions → Refresh contributions → Run workflow 手动更新。

- 仅使用仓库自带的 `github.token`，不需要个人访问令牌或第三方统计服务。
- 图片展示 GitHub 返回的最近 26 周贡献，不是全部历史；公开活动受 GitHub 的可见性规则影响。
- 请求失败、身份不匹配或数据不合法时工作流失败并保留上一次有效图片，绝不会用随机数据或假零值替代。
- 图片带生成时间。GitHub 图片代理可能缓存，工作流定时任务也可能延迟；官方个人页是实时核对入口。
- 公开仓库连续 60 天无活动，GitHub 可能暂停定时任务。重新启用工作流即可。
- 工作流仅提交贡献图，由 Actions bot 署名；不会为了装饰伪造个人提交记录。

验证：`python3 -m unittest discover -s tests -p 'test_contributions.py' -v`。

## GitHub 可行布局

README 使用 GitHub 支持的 Markdown、`picture`、`source`、`img` 和链接，不依赖自定义页面 CSS、脚本或嵌入网页。页面背景由读者的 GitHub 主题决定；素材自带深色背景，在浅色主题也能阅读。GIF 提供可靠动态，SVG 提供静态回退。

官方文档：

- [Profile README](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
- [Images and picture](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#images)
- [Supported non-code formats](https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files)
- [Scheduled workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
