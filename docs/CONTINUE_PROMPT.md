# Continue Prompt

复制下面这段给新机器/新 Codex 线程：

```text
你现在接手 `/home/yiyuldx/swe` 里的 SWE-Trace / SWE-Code-Agent 项目。代码在 `/home/yiyuldx/swe`，大文件和生成数据在 `/data/yiyuldx/swe`。请先阅读：

- `/home/yiyuldx/AGENTS.md`（如果存在）
- `/home/yiyuldx/swe/docs/HANDOFF.md`
- `/home/yiyuldx/swe/README.md`
- `/home/yiyuldx/swe/reports/progress.html`

项目目标：为大模型算法实习准备一个两周冲刺项目，方向是 Agent Post-training、SFT 数据、Code Agent 评测、大模型数据、AI Coding 应用算法。项目定位不是从零写 Code Agent，而是构建 Code Agent 轨迹采集、失败诊断、SFT/DPO/reward 数据构造和评测/小规模后训练验证链路。

当前已完成：

- swetrace 核心 schema、RunStore、fake adapter
- run_task/run_batch CLI
- mini-SWE-agent adapter skeleton
- failure taxonomy 和 rule-based labeler
- SFT-plan / SFT-patch / SFT-debug / DPO pair / reward-log builders
- SWE-bench Lite hf-mirror 下载脚本
- Docker preflight 脚本
- progress HTML 报告页
- SWE-bench task selector、Docker image prepare manifest、manual review queue CLI
- pytest 上次为 26 passed

当前主要阻塞：

- Docker 可用，但当前 Codex 进程需要用 `sg docker -c '...'` 继承 docker 组。
- 非 sqlfluff 镜像下载较慢；大文件、cache、runs、outputs 都必须放在 `/data/yiyuldx/swe`。

请你不要重新设计项目，直接继续执行下一步：

1. 在 `/home/yiyuldx/swe` 使用 `/home/yiyuldx/birdNet/.venv`。
2. 安装依赖并运行 `/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q`。
3. 运行 `./scripts/check_docker.sh`。
4. 如果 Docker 可用，运行 `./scripts/download_swebench_lite.sh`。
5. 然后运行：
   `SWETRACE_MINI_SUBSET=/data/yiyuldx/swe/cache/swebench_lite SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 ./scripts/run_mini_smoke.sh`
6. 如果生成真实 `.traj.json`，检查 `trajectory.jsonl`、`patch.diff`、`test.log`、`report.json`，必要时修正 `swetrace/adapters/mini_swe_agent.py` 的 parser 并加测试。
7. 跑 5-10 个 SWE-bench Lite dev tasks，开始积累真实 runs。
8. 构建真实 SFT/debug/reward 数据，并更新 `/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl`。
9. 每次项目推进都更新 `/home/yiyuldx/swe/reports/progress.html`，并保持 GitHub 同步到 `https://github.com/yiyu0716/swe-code-agent.git`。

请用中文向我汇报。遇到 Docker、权限、数据集访问、模型 API key 等阻塞时，先尝试替代方案；确实需要我提供权限或密钥时再说明。
```
