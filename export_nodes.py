#!/usr/bin/env python3
import sqlite3
import json
import base64
import urllib.parse
import sys
import os
import re
from typing import Optional, Dict, List, Any


class V2rayNodeExporter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        if not uuid_str:
            return False
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))

    def has_history_table(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ProfileExItemHistory'")
        return cursor.fetchone() is not None

    def get_best_nodes(self, limit: int = 20, min_tests: int = 3, min_success_rate: float = 50.0) -> List[Dict[str, Any]]:
        if not self.has_history_table():
            print("Warning: ProfileExItemHistory table not found. Using ProfileExItem for basic node info.")
            return self.get_nodes_from_profile_item(limit)

        query = """
        WITH NodeStats AS (
            SELECT
                h.IndexId,
                pi.Remarks,
                pi.Address,
                pi.Port,
                pi.ConfigType,
                pi.ConfigVersion,
                pi.Id,
                pi.AlterId,
                pi.Security,
                pi.Network,
                pi.HeaderType,
                pi.RequestHost,
                pi.Path,
                pi.StreamSecurity,
                pi.AllowInsecure,
                pi.Sni,
                pi.Alpn,
                pi.Fingerprint,
                pi.Flow,
                pi.PublicKey,
                pi.ShortId,
                pi.Ports,
                pi.CertSha,
                COUNT(*) AS TotalTests,
                SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
                ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
                ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
                MIN(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MinDelay,
                MAX(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MaxDelay,
                MAX(h.TestTime) AS LastTestTime,
                ROUND(
                    AVG(CASE WHEN h.Success = 1 THEN h.Delay * h.Delay ELSE NULL END) -
                    AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) *
                    AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END),
                    0
                ) AS Variance
            FROM ProfileExItemHistory h
            INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
            GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port, pi.ConfigType, pi.ConfigVersion,
                     pi.Id, pi.AlterId, pi.Security, pi.Network, pi.HeaderType, pi.RequestHost,
                     pi.Path, pi.StreamSecurity, pi.AllowInsecure, pi.Sni, pi.Alpn, pi.Fingerprint,
                     pi.Flow, pi.PublicKey, pi.ShortId, pi.Ports, pi.CertSha
            HAVING COUNT(*) >= ?
        ),
        DelayRange AS (
            SELECT
                MIN(AvgDelay) AS MinAvgDelay,
                MAX(AvgDelay) AS MaxAvgDelay
            FROM NodeStats
            WHERE AvgDelay IS NOT NULL
        )
        SELECT
            ns.*,
            ROUND(
                ns.SuccessRate * 60 +
                CASE
                    WHEN dr.MinAvgDelay = dr.MaxAvgDelay THEN 40
                    ELSE 40 * (1 - (ns.AvgDelay - dr.MinAvgDelay) * 1.0 / (dr.MaxAvgDelay - dr.MinAvgDelay))
                END -
                CASE
                    WHEN ns.Variance < 1000 THEN 0
                    WHEN ns.Variance < 5000 THEN 5
                    WHEN ns.Variance < 10000 THEN 10
                    ELSE 20
                END,
                2
            ) AS OverallScore
        FROM NodeStats ns, DelayRange dr
        WHERE ns.SuccessRate >= ?
        ORDER BY OverallScore DESC, ns.AvgDelay ASC
        LIMIT ?
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (min_tests, min_success_rate, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_nodes_from_profile_item(self, limit: int = 20) -> List[Dict[str, Any]]:
        query = """
        SELECT
            pi.IndexId,
            pi.Remarks,
            pi.Address,
            pi.Port,
            pi.ConfigType,
            pi.ConfigVersion,
            pi.Id,
            pi.AlterId,
            pi.Security,
            pi.Network,
            pi.HeaderType,
            pi.RequestHost,
            pi.Path,
            pi.StreamSecurity,
            pi.AllowInsecure,
            pi.Sni,
            pi.Alpn,
            pi.Fingerprint,
            pi.Flow,
            pi.PublicKey,
            pi.ShortId,
            pi.Ports,
            pi.CertSha,
            pe.Delay,
            pe.Speed,
            pe.Message
        FROM ProfileItem pi
        LEFT JOIN ProfileExItem pe ON pi.IndexId = pe.IndexId
        WHERE pi.Address IS NOT NULL AND pi.Address != ''
        ORDER BY pe.Delay ASC
        LIMIT ?
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_node_by_index_id(self, index_id: str) -> Optional[Dict[str, Any]]:
        query = """
        SELECT
            IndexId,
            ConfigType,
            ConfigVersion,
            Address,
            Port,
            Id,
            AlterId,
            Security,
            Network,
            Remarks,
            HeaderType,
            RequestHost,
            Path,
            StreamSecurity,
            AllowInsecure,
            Subid,
            IsSub,
            Flow,
            Sni,
            Alpn,
            CoreType,
            PreSocksPort,
            Fingerprint,
            DisplayLog,
            PublicKey,
            ShortId,
            SpiderX,
            Mldsa65Verify,
            Extra,
            MuxEnabled,
            Cert,
            CertSha,
            EchConfigList,
            EchForceQuery,
            Ports
        FROM ProfileItem
        WHERE IndexId = ?
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (index_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            IndexId,
            ConfigType,
            ConfigVersion,
            Address,
            Port,
            Id,
            AlterId,
            Security,
            Network,
            Remarks,
            HeaderType,
            RequestHost,
            Path,
            StreamSecurity,
            AllowInsecure,
            Subid,
            IsSub,
            Flow,
            Sni,
            Alpn,
            CoreType,
            PreSocksPort,
            Fingerprint,
            DisplayLog,
            PublicKey,
            ShortId,
            SpiderX,
            Mldsa65Verify,
            Extra,
            MuxEnabled,
            Cert,
            CertSha,
            EchConfigList,
            EchForceQuery,
            Ports
        FROM ProfileItem
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def to_vmess_uri(self, node: Dict[str, Any]) -> str:
        vmess_qr = {
            "v": node.get("ConfigVersion", 2),
            "ps": node.get("Remarks", ""),
            "add": node.get("Address", ""),
            "port": node.get("Port", 0),
            "id": node.get("Id", ""),
            "aid": node.get("AlterId", 0),
            "scy": node.get("Security", "auto"),
            "net": node.get("Network", "tcp"),
            "type": node.get("HeaderType", ""),
            "host": node.get("RequestHost", ""),
            "path": node.get("Path", ""),
            "tls": node.get("StreamSecurity", ""),
            "sni": node.get("Sni", ""),
            "alpn": node.get("Alpn", ""),
            "fp": node.get("Fingerprint", ""),
            "insecure": "1" if node.get("AllowInsecure") == "1" else "0"
        }
        json_str = json.dumps(vmess_qr, separators=(',', ':'))
        b64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return f"vmess://{b64_str}"

    def to_vless_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        uuid = node.get("Id", "")
        remarks = node.get("Remarks", "")

        params = {
            "encryption": node.get("Security", "none"),
            "type": node.get("Network", "tcp"),
            "security": node.get("StreamSecurity", ""),
            "sni": node.get("Sni", ""),
            "fp": node.get("Fingerprint", ""),
            "alpn": node.get("Alpn", ""),
            "flow": node.get("Flow", ""),
            "headerType": node.get("HeaderType", ""),
            "host": node.get("RequestHost", ""),
            "path": node.get("Path", ""),
            "allowInsecure": "1" if node.get("AllowInsecure") == "1" else "0"
        }

        query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v])
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"vless://{uuid}@{address}:{port}?{query}{remark}"

    def to_shadowsocks_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        method = node.get("Security", "")
        password = node.get("Id", "")
        remarks = node.get("Remarks", "")

        user_info = base64.b64encode(f"{method}:{password}".encode('utf-8')).decode('utf-8')
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"ss://{user_info}@{address}:{port}{remark}"

    def to_trojan_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        password = node.get("Id", "")
        remarks = node.get("Remarks", "")

        params = {
            "security": node.get("StreamSecurity", ""),
            "sni": node.get("Sni", ""),
            "fp": node.get("Fingerprint", ""),
            "alpn": node.get("Alpn", ""),
            "type": node.get("Network", "tcp"),
            "host": node.get("RequestHost", ""),
            "path": node.get("Path", ""),
            "allowInsecure": "1" if node.get("AllowInsecure") == "1" else "0"
        }

        query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v])
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"trojan://{password}@{address}:{port}?{query}{remark}"

    def to_hysteria2_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        password = node.get("Id", "")
        remarks = node.get("Remarks", "")

        params = {
            "sni": node.get("Sni", ""),
            "obfs": "salamander" if node.get("Path") else "",
            "obfs-password": node.get("Path", ""),
            "pinSHA256": node.get("CertSha", "")
        }

        query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v])
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"hy2://{password}@{address}:{port}?{query}{remark}"

    def to_tuic_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        uuid = node.get("Id", "")
        key = node.get("Security", "")
        remarks = node.get("Remarks", "")

        params = {
            "sni": node.get("Sni", ""),
            "congestion_control": node.get("HeaderType", ""),
            "alpn": node.get("Alpn", ""),
            "allowInsecure": "1" if node.get("AllowInsecure") == "1" else "0"
        }

        query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v])
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"tuic://{uuid}:{key}@{address}:{port}?{query}{remark}"

    def to_wireguard_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        private_key = node.get("Id", "")
        remarks = node.get("Remarks", "")

        params = {
            "publickey": node.get("PublicKey", ""),
            "reserved": node.get("Path", ""),
            "address": node.get("RequestHost", ""),
            "mtu": node.get("ShortId", "")
        }

        query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v])
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"wireguard://{private_key}@{address}:{port}?{query}{remark}"

    def to_socks_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        user = node.get("Id", "")
        password = node.get("Security", "")
        remarks = node.get("Remarks", "")

        pw = base64.b64encode(f"{password}:{user}".encode('utf-8')).decode('utf-8')
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"socks://{pw}@{address}:{port}{remark}"

    def to_http_uri(self, node: Dict[str, Any]) -> str:
        address = node.get("Address", "")
        port = node.get("Port", 0)
        user = node.get("Id", "")
        password = node.get("Security", "")
        remarks = node.get("Remarks", "")

        user_info = f"{user}:{password}" if user else ""
        remark = f"#{urllib.parse.quote(remarks)}" if remarks else ""
        return f"http://{user_info}@{address}:{port}{remark}"

    def node_to_uri(self, node: Dict[str, Any]) -> Optional[str]:
        config_type = node.get("ConfigType", 0)
        index_id = node.get("IndexId", "unknown")
        remarks = node.get("Remarks", "")

        try:
            if config_type == 1:
                return self.to_vmess_uri(node)
            elif config_type == 6:
                uuid = node.get("Id", "")
                if not self.is_valid_uuid(uuid):
                    print(f"Warning: Invalid UUID for node '{remarks}' (IndexId: {index_id}): {uuid}")
                    return None
                return self.to_vless_uri(node)
            elif config_type == 2:
                return self.to_shadowsocks_uri(node)
            elif config_type == 5:
                return self.to_trojan_uri(node)
            elif config_type == 7:
                return self.to_hysteria2_uri(node)
            elif config_type == 8:
                return self.to_tuic_uri(node)
            elif config_type == 9:
                return self.to_wireguard_uri(node)
            elif config_type == 3:
                user = node.get("Id", "")
                password = node.get("Security", "")
                if not user or not password:
                    print(f"Warning: Missing credentials for SOCKS node '{remarks}' (IndexId: {index_id})")
                    return None
                return self.to_socks_uri(node)
            elif config_type == 4:
                return self.to_http_uri(node)
            else:
                print(f"Warning: Unknown config type {config_type} for node '{remarks}' (IndexId: {index_id})")
                return None
        except Exception as e:
            print(f"Error converting node '{remarks}' (IndexId: {index_id}): {e}")
            return None

    def export_best_nodes(self, output_file: str = None, limit: int = 20, min_tests: int = 3, min_success_rate: float = 50.0) -> Dict[str, Any]:
        nodes = self.get_best_nodes(limit, min_tests, min_success_rate)
        uris = []
        skipped = []

        for node in nodes:
            uri = self.node_to_uri(node)
            if uri:
                uris.append(uri)
            else:
                skipped.append(node.get("Remarks", "Unknown"))

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(uris))

        return {
            "uris": uris,
            "total": len(nodes),
            "exported": len(uris),
            "skipped": len(skipped),
            "skipped_nodes": skipped
        }

    def export_all_nodes(self, output_file: str = None) -> Dict[str, Any]:
        nodes = self.get_all_nodes()
        uris = []
        skipped = []

        for node in nodes:
            uri = self.node_to_uri(node)
            if uri:
                uris.append(uri)
            else:
                skipped.append(node.get("Remarks", "Unknown"))

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(uris))

        return {
            "uris": uris,
            "total": len(nodes),
            "exported": len(uris),
            "skipped": len(skipped),
            "skipped_nodes": skipped
        }


def show_help():
    print("V2rayN Node Exporter - Export nodes from v2rayN database")
    print()
    print("Usage: python export_nodes.py <database_path> [output_file] [options]")
    print()
    print("Arguments:")
    print("  database_path    Path to v2rayN database file (guiNDB.db)")
    print("  output_file      Optional output file path (default: print to stdout)")
    print()
    print("Options:")
    print("  --all            Export all nodes instead of best nodes")
    print("  --limit N        Number of nodes to export (default: 20)")
    print("  --min-tests N    Minimum number of tests required (default: 3)")
    print("  --min-success-rate N  Minimum success rate percentage (default: 50)")
    print()
    print("Examples:")
    print("  python export_nodes.py guiNDB.db nodes.txt")
    print("  python export_nodes.py guiNDB.db nodes.txt --all")
    print("  python export_nodes.py guiNDB.db nodes.txt --limit 10 --min-tests 5 --min-success-rate 70")
    print()
    print("Database locations:")
    print("  Windows: v2rayN\\v2rayN\\bin\\Debug\\net8.0-windows10.0.17763\\guiConfigs\\guiNDB.db")
    print("  macOS:   ~/Library/Application Support/v2rayN/guiNDB.db")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        sys.exit(0)

    db_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None

    limit = 20
    min_tests = 3
    min_success_rate = 50.0
    export_all = False

    i = 2 if output_file else 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--all':
            export_all = True
        elif arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 1
        elif arg == '--min-tests' and i + 1 < len(sys.argv):
            min_tests = int(sys.argv[i + 1])
            i += 1
        elif arg == '--min-success-rate' and i + 1 < len(sys.argv):
            min_success_rate = float(sys.argv[i + 1])
            i += 1
        i += 1

    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    exporter = V2rayNodeExporter(db_path)
    try:
        exporter.connect()

        if export_all:
            print(f"Exporting all nodes...")
            result = exporter.export_all_nodes(output_file)
        else:
            print(f"Exporting best {limit} nodes (min tests: {min_tests}, min success rate: {min_success_rate}%)...")
            result = exporter.export_best_nodes(output_file, limit, min_tests, min_success_rate)

        print(f"\nTotal nodes found: {result['total']}")
        print(f"Successfully exported: {result['exported']}")
        print(f"Skipped (invalid): {result['skipped']}")

        if result['skipped'] > 0:
            print(f"\nSkipped nodes:")
            for node in result['skipped_nodes']:
                print(f"  - {node}")

        if output_file:
            print(f"\nSaved to: {output_file}")
        else:
            print("\n" + "=" * 80)
            print("Node URIs (copy and paste into v2rayN):")
            print("=" * 80)
            for uri in result['uris']:
                print(uri)
            print("=" * 80)

    finally:
        exporter.close()


if __name__ == "__main__":
    main()
