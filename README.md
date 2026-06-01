# OpenStack AI Agent

一个基于 AI 的 OpenStack Pike 集群智能监控和故障诊断系统。

## 功能特性

- 🚀 **实时监控** - 对接 OpenStack Pike 版本，实时采集组件运行状态
- 🔔 **智能告警** - 多层级故障检测和告警规则引擎
- 🧠 **AI 根因分析** - 基于机器学习的异常检测和智能诊断
- 📊 **数据可视化** - 完整的监控仪表板和告警展示
- 🔧 **易于部署** - Docker 容器化部署，开箱即用

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│           AI 智能体前端 (Web Dashboard)                 │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│            API 网关 / 编排层                              │
├──────────────────┬──────────────────┬──────────────────┤
│  监控告警模块    │  根因分析模块    │  故障诊断模块    │
└──────────────────┼──────────────────┼──────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│         数据采集 & 存储层                                │
├──────────────────┬──────────────────┬──────────────────┤
│  OpenStack SDK   │   时间序列DB    │   日志存储       │
│  (python-client) │   (InfluxDB)     │                 │
└──────────────────┴──────────────────┴──────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│         OpenStack Pike 集群                             │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.8+
- OpenStack Pike 或更高版本
- InfluxDB (可选)
- Docker & Docker Compose (可选)

### 安装

```bash
# 克隆项目
git clone https://github.com/bayunxu/openstack-agent.git
cd openstack-agent

# 安装依赖
pip install -r requirements.txt

# 配置 OpenStack 认证
cp config/openstack.yaml.example config/openstack.yaml
# 编辑 config/openstack.yaml，填写 OpenStack 凭证
```

### 运行

```bash
# 启动 API 服务
python -m src.agent.api.main

# 启动监控采集
python -m src.agent.core.monitoring

# 启动根因分析
python -m src.agent.ai.anomaly_detection
```

### Docker 部署

```bash
cd docker
docker-compose up -d
```

## 文档

- [架构设计](docs/architecture.md)
- [API 文档](docs/api-docs.md)
- [部署指南](docs/deployment-guide.md)
- [配置说明](docs/configuration.md)

## 许可证

MIT License

## 联系方式

作者：bayunxu

---

**最后更新**: 2026-06-01
