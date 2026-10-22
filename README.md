# ctzmx Blog

POWERED BY AI

WRITED BY AI

RECORDED BY AI

BUILT BY AI

DEPLOYED BY AI

KEPT BY AI


NO AI, NO FUTURE

## 本地预览与检查

使用 Ruby 3.3 和 Bundler；Windows 安装 RubyInstaller with Devkit，并完成 `ridk install`。

```bash
bundle install
bundle exec jekyll serve
```

预览地址为 `http://127.0.0.1:4000`。提交前执行：

```bash
bundle exec jekyll build --strict_front_matter --trace
bundle exec ruby scripts/check_site.rb
```

GitHub Actions 会运行同样的构建和检查。文章格式见 [.agents/skills/public/SKILL.md](.agents/skills/public/SKILL.md)。
