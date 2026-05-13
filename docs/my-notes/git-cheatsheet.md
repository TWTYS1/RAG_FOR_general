# Git 常用指令速查表

## 1. 基础配置

```bash
git --version
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
git config --global --list
```

## 2. 创建与克隆仓库

```bash
git init
git clone <仓库地址>
git clone <仓库地址> <本地目录名>
```

## 3. 查看状态与历史

```bash
git status
git status -s
git log
git log --oneline
git log --oneline --graph --decorate --all
git show <commit_id>
```

## 4. 添加与提交

```bash
git add <文件名>
git add .
git add -A
git commit -m "提交说明"
git commit -am "提交说明"
```

说明：

- `git add .` 添加当前目录下的改动。
- `git add -A` 添加所有改动，包括删除的文件。
- `git commit -am` 只适用于已经被 Git 跟踪过的文件。

## 5. 分支操作

```bash
git branch
git branch -a
git branch <分支名>
git checkout <分支名>
git checkout -b <新分支名>
git switch <分支名>
git switch -c <新分支名>
git branch -d <分支名>
git branch -D <分支名>
```

## 6. 合并与变基

```bash
git merge <分支名>
git rebase <分支名>
git rebase --continue
git rebase --abort
```

常见流程：

```bash
git switch main
git pull
git switch feature/demo
git rebase main
```

## 7. 远程仓库

```bash
git remote -v
git remote add origin <仓库地址>
git remote set-url origin <新仓库地址>
git fetch
git fetch --all
git pull
git pull --rebase
git push
git push -u origin <分支名>
git push origin <分支名>
```

## 8. 撤销与恢复

```bash
git restore <文件名>
git restore .
git restore --staged <文件名>
git reset HEAD <文件名>
git reset --soft HEAD~1
git reset --mixed HEAD~1
git reset --hard HEAD~1
git revert <commit_id>
```

说明：

- `git restore` 撤销工作区改动。
- `git restore --staged` 取消暂存。
- `git reset --soft` 撤销提交但保留暂存。
- `git reset --mixed` 撤销提交并取消暂存，保留文件改动。
- `git reset --hard` 会丢弃改动，使用前要确认。
- `git revert` 生成一个新的反向提交，适合已经推送到远程的提交。

## 9. 暂存工作区

```bash
git stash
git stash push -m "说明"
git stash list
git stash pop
git stash apply
git stash drop
git stash clear
```

## 10. 标签

```bash
git tag
git tag <标签名>
git tag -a <标签名> -m "标签说明"
git push origin <标签名>
git push origin --tags
git tag -d <标签名>
git push origin :refs/tags/<标签名>
```

## 11. 差异比较

```bash
git diff
git diff --staged
git diff <分支1>..<分支2>
git diff <commit_id1> <commit_id2>
```

## 12. 查看文件归属与排查问题

```bash
git blame <文件名>
git bisect start
git bisect bad
git bisect good <commit_id>
git bisect reset
```

## 13. 常用组合命令

```bash
git status
git add .
git commit -m "feat: add new feature"
git pull --rebase
git push
```

```bash
git switch -c feature/demo
git add .
git commit -m "feat: implement demo"
git push -u origin feature/demo
```

## 14. 常见问题处理

### 修改最后一次提交信息

```bash
git commit --amend -m "新的提交说明"
```

### 把当前分支更新到远程最新状态

```bash
git fetch origin
git rebase origin/main
```

### 删除远程分支

```bash
git push origin --delete <分支名>
```

### 清理未跟踪文件

```bash
git clean -n
git clean -fd
```

说明：

- `git clean -n` 只预览将被删除的文件。
- `git clean -fd` 会真正删除未跟踪文件和目录。

## 15. 推荐提交信息前缀

```text
feat: 新功能
fix: 修复问题
docs: 文档修改
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建、工具或杂项
```

