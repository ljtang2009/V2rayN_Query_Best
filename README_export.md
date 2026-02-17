# V2rayN 节点导出工具

这个工具可以从 v2rayN 的数据库中导出优秀节点，生成可以直接复制到 v2rayN 中的节点链接。

## 特性

- ✅ 支持 Windows 和 macOS
- ✅ 无需安装任何外部依赖（使用 Python 标准库）
- ✅ 支持多种协议：VMess, VLESS, Shadowsocks, Trojan, Hysteria2, TUIC, WireGuard, SOCKS, HTTP
- ✅ 基于历史测试数据智能评分，自动筛选优秀节点
- ✅ 支持导出所有节点或仅导出优秀节点

## 使用方法

### 1. 准备 Python 环境

确保已安装 Python 3.7 或更高版本：

```bash
# 检查 Python 版本
python --version
# 或
python3 --version
```

### 2. 找到数据库文件

v2rayN 的数据库文件通常位于：

**Windows:**
```
v2rayN\v2rayN\bin\Debug\net8.0-windows10.0.17763\guiConfigs\guiNDB.db
```

**macOS:**
```
~/Library/Application Support/v2rayN/guiNDB.db
```

### 3. 启动数据库客户端

下列以DBeaver为例，其他数据库客户端也类似。

#### 下载SQLite驱动

下载地址（选一个即可）：

直接下载链接（示例：3.51.2.0）：
https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.51.2.0/sqlite-jdbc-3.51.2.0.jar
或者打开目录自己选版本：
https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/

#### 运行DBeaver

1. 打开DBeaver
2. 点击"数据库" → "新建数据库连接"
3. 选择"SQLite"
4. 点击"下一步"

#### 在 DBeaver 里手动指定驱动

按下面步骤操作：

1. 在 DBeaver 中，右键你的 SQLite 连接 → “编辑连接(Edit Connection)”。
1. 在弹出窗口左侧选中 “驱动设置(Driver settings)” 或 “编辑驱动设置(Edit driver settings)”。
1. 切到 “库(Libraries)” 标签页。
1. 你会看到类似 org.xerial:sqlite-jdbc:RELEASE 这样的条目，选中它，点击“删除(Remove)”，把原来的自动下载条目删掉。
1. 点击 “添加文件(Add File)”，选中你刚才下载的 sqlite-jdbc-3.51.2.0.jar。
1. 确保驱动信息大致是：
   - 驱动名：`SQLite`
   - 类名：org.sqlite.JDBC（一般会自动带出来，如果没有就手动填）
1. 点 “确定” 保存驱动设置。
1. 回到连接设置，填好:
JDBC URL：jdbc:sqlite:/路径/到/你的数据库文件.db
用户名/密码一般可以留空（SQLite 默认没有账号）。
1. 点击 “测试连接(Test Connection)”，应该就能连上了。

### 4. 运行导出脚本

#### 导出优秀节点（默认）

导出综合评分最高的 20 个节点：

```bash
python export_nodes.py <数据库路径> [输出文件]
```

示例：
```bash
# Windows
python export_nodes.py "D:\APP\v2rayN-windows-64-SelfContained\guiConfigs\guiNDB.db" nodes.txt

# macOS
python3 export_nodes.py ~/Library/Application\ Support/v2rayN/guiNDB.db nodes.txt
```

#### 导出所有节点

```bash
python export_nodes.py <数据库路径> [输出文件] --all
```

#### 自定义导出参数

```bash
python export_nodes.py <数据库路径> [输出文件] --limit N --min-tests N --min-success-rate N
```

参数说明：
- `--limit N`: 导出节点数量（默认：20）
- `--min-tests N`: 最少测试次数（默认：3）
- `--min-success-rate N`: 最小成功率百分比（默认：50）

示例：
```bash
# 导出前 10 个节点，至少测试 5 次，成功率 >= 70%
python export_nodes.py guiNDB.db nodes.txt --limit 10 --min-tests 5 --min-success-rate 70
```

#### 仅显示结果（不保存到文件）

```bash
python export_nodes.py <数据库路径>
```

### 4. 导入到 v2rayN

1. 打开 v2rayN
2. 点击"订阅" → "从剪贴板导入"
3. 复制导出的节点链接
4. 粘贴并导入

或者：
1. 打开导出的文本文件
2. 复制所有内容
3. 在 v2rayN 中从剪贴板导入

## 评分算法

综合评分 = 成功率 × 60 + (1 - 标准化延迟) × 40 - 延迟波动惩罚

- **成功率权重**：60%
- **延迟权重**：40%
- **延迟波动惩罚**：根据方差计算
  - 方差 < 1000：不惩罚
  - 方差 < 5000：惩罚 5 分
  - 方差 < 10000：惩罚 10 分
  - 方差 >= 10000：惩罚 20 分

## 支持的协议

| 协议 | ConfigType | URI 格式 |
|------|------------|----------|
| VMess | 1 | vmess:// |
| Shadowsocks | 2 | ss:// |
| SOCKS | 3 | socks5:// |
| HTTP | 4 | http:// |
| Trojan | 5 | trojan:// |
| VLESS | 6 | vless:// |
| Hysteria2 | 7 | hy2:// |
| TUIC | 8 | tuic:// |
| WireGuard | 9 | wireguard:// |

## 注意事项

1. 确保数据库文件未被 v2rayN 锁定（关闭 v2rayN 或复制数据库文件）
2. 导出的节点链接可以直接复制到 v2rayN 中使用
3. 建议定期测试节点以积累历史数据，这样筛选结果会更准确
4. 某些协议可能需要特定的 v2rayN 版本支持
5. **SOCKS 节点**：v2rayN 支持 SOCKS 代理节点，但需要完整的用户名和密码配置
6. **VLESS 节点**：必须使用有效的 UUID 格式（8-4-4-4-12 的十六进制格式），无效的 UUID 会被跳过
7. 程序会自动跳过无效的节点，并在输出中显示被跳过的节点列表

## 故障排除

### 问题：找不到数据库文件

**解决方案：**
- Windows：检查 v2rayN 安装目录下的 `guiConfigs` 文件夹
- macOS：检查 `~/Library/Application Support/v2rayN/` 目录

### 问题：数据库被锁定

**解决方案：**
- 关闭 v2rayN 后再运行脚本
- 或者复制数据库文件到其他位置

### 问题：Python 版本过低

**解决方案：**
- 升级到 Python 3.7 或更高版本
- 访问 https://www.python.org/downloads/ 下载最新版本

### 问题：导出的节点无法导入

**解决方案：**
- 检查节点配置是否完整（地址、端口、密码等）
- 某些协议可能需要特定的 v2rayN 版本
- 查看 v2rayN 日志获取详细错误信息

## 示例输出

```
Exporting best 20 nodes (min tests: 3, min success rate: 50.0%)...

Total nodes found: 20
Successfully exported: 16
Skipped (invalid): 4

Skipped nodes:
  - TW (Invalid UUID)
  - KR (Invalid UUID)
  - HK (Invalid UUID)
  - 美国 (Missing credentials)

Saved to: nodes.txt
```

导出的文件内容示例：
```
vmess://eyJ2IjoyLCJwcyI6IuWIm+eUqOaYr+a4h...
vless://uuid@address:port?encryption=none&type=tcp...
ss://c2hhZG93c29ja3M6cGFzc3dvcmQ=@address:port#remark
trojan://password@address:port?security=tls...
socks://cGFzc3dvcmQ6dXNlcm5hbWU=@address:port#remark
```

## 许可证

本工具遵循 v2rayN 项目的许可证。
