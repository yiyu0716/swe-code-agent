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
- orphan raw mini trajectory 恢复 CLI：`recover_mini_runs.sh`
- SWE-bench parquet metadata 回填 CLI：`enrich_swebench_run_tasks.sh`
- 人工 review annotation CLI：`annotate_review.sh`
- 人工 review Web UI：`serve_review_ui.sh`，默认 <http://127.0.0.1:20039/review>
- gold-patch vs agent-patch DPO pair 构建
- official-aware v0.2 数据构建脚本：`build_official_v02.sh`
- 当前 `/data/yiyuldx/swe/outputs/datasets/v0.2` 已有 SFT plan 41、patch 41、DPO main 60、debug cases 60、reward logs 103，`train_ready=true`；DPO chosen source 为 `agent_resolved_patch=1`、`swebench_gold_patch=59`
- 旧 root JSONL 已归档到 `/data/yiyuldx/swe/outputs/datasets/legacy_root_20260605`；do not train on those root JSONL files 或 v0.1 filtered samples
- 当前 SWE-bench Lite dev 本地任务已跑完；下一批优先冻结 v0.2 训练快照、跑数据格式 smoke 和小规模 SFT/DPO dry run

当前主要阻塞：

- Docker 可用，但当前 Codex 进程需要用 `sg docker -c '...'` 继承 docker 组。
- Docker data-root 已迁到 `/data/yiyuldx/docker`；后续拉镜像主要受网络/registry 速度限制。
- 大文件、cache、runs、outputs 都必须放在 `/data/yiyuldx/swe`。

请你不要重新设计项目，直接继续执行下一步：

1. 在 `/home/yiyuldx/swe` 使用 `/home/yiyuldx/birdNet/.venv`。
2. 安装依赖并运行 `/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q`。
3. 运行 `./scripts/check_docker.sh`。
4. 如果 Docker 可用，运行 `./scripts/download_swebench_lite.sh`。
5. 然后运行：
   `SWETRACE_MINI_SUBSET=/data/yiyuldx/swe/cache/swebench_lite SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 ./scripts/run_mini_smoke.sh`
6. 如果生成真实 `.traj.json`，检查 `trajectory.jsonl`、`patch.diff`、`test.log`、`report.json`，必要时修正 `swetrace/adapters/mini_swe_agent.py` 的 parser 并加测试。
7. 先检查 task selector 是否仍返回 0 个 dev candidates；若是，转入 v0.2 训练快照、人工复核与数据质检。
8. 使用 `scripts/serve_review_ui.sh` 打开网页标注，或使用 `scripts/annotate_review.sh` 记录人工标签、patch 质量和 train/eval inclusion。
9. 检查 official-aware 数据集 `/data/yiyuldx/swe/outputs/datasets/v0.2/manifest.json`、`dpo_main.jsonl`、`sft_patch.jsonl`、`reward_logs.jsonl` 和 `/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl`；不要使用 `/data/yiyuldx/swe/outputs/datasets` 根目录旧 JSONL、`legacy_root_20260605` 或 v0.1 作为训练输入。
10. 每次项目推进都更新 `/home/yiyuldx/swe/reports/progress.html`，并保持 GitHub 同步到 `https://github.com/yiyu0716/swe-code-agent.git`。

请用中文向我汇报。遇到 Docker、权限、数据集访问、模型 API key 等阻塞时，先尝试替代方案；确实需要我提供权限或密钥时再说明。
```
