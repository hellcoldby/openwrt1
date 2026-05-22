#!/bin/sh
# ============================================================
#  RG100A-BA First Boot Auto Setup (uci-defaults)
#  首次启动时自动执行：LAN IP + WAN VLAN + 防火墙
#  执行完毕后自删除
# ============================================================

echo "============================================"
echo "  TIANBEI RG100A-BA - First Boot Setup"
echo "============================================"

# ---- Step 1: LAN IP 改为 192.168.11.1 (避免与上级路由 192.168.1.1 冲突) ----
echo "[1/5] 配置 LAN IP = 192.168.11.1..."

uci set network.lan.ipaddr='192.168.11.1'
uci set network.lan.netmask='255.255.255.0'

# DHCP 地址池随之更新
uci set dhcp.lan.start='100'
uci set dhcp.lan.limit='150'
uci add_list dhcp.lan.dhcp_option='6,192.168.11.1'

echo "  LAN IP: 192.168.11.1/24 | DHCP: .100-.249"

# ---- Step 2: Switch VLAN (Port0 → WAN) ----
echo "[2/5] 配置交换机 VLAN (Port0=WAN)..."

# VLAN1 LAN: Ports 1-3 + CPU(tagged)
if uci -q get switch.@switch_vlan[0] >/dev/null; then
    uci set switch.@switch_vlan[0].ports='1 2 3 8t'
fi

# VLAN2 WAN: Port0 + CPU(tagged)
if ! uci -q get switch.@switch_vlan[1] >/dev/null; then
    uci add switch vlan='switch0' > /dev/null
fi
uci set switch.@switch_vlan[1].vlan='2'
uci set switch.@switch_vlan[1].vid='2'
uci set switch.@switch_vlan[1].ports='0 8t'

echo "  LAN: Ports 1,2,3 | WAN: Port0"

# ---- Step 3: WAN 网络接口 ----
echo "[3/5] 创建 WAN 接口..."

if ! uci -q get network.wan >/dev/null; then
    uci set network.wan=interface
fi
uci set network.wan.device='eth0.2'
uci set network.wan.proto='dhcp'
uci set network.wan.auto='1'

echo "  WAN = eth0.2 (DHCP)"

# ---- Step 4: 防火墙 ----
echo "[4/5] 配置防火墙..."

# 确保 wan zone 包含 wan 接口
has_wan=$(uci show firewall | grep -c '@zone\[1\].network=.*wan' || true)
if [ "$has_wan" -eq 0 ]; then
    wan_zone_idx=$(uci show firewall | grep '\[zone\]' | tail -n 1 | grep -o '\[[0-9]*\]' | tr -d '[]')
    if [ -z "$wan_zone_idx" ]; then
        wan_zone_idx=1
    fi
    uci add_list firewall.@zone[$wan_zone_idx].network='wan'
fi

echo "  WAN zone linked"

# ---- 软件源切换为清华镜像 ----
echo ""
echo "[5/5] 切换 opkg 软件源为清华镜像..."

sed -i 's|https://downloads.openwrt.org|http://mirrors.tuna.tsinghua.edu.cn/openwrt|g' /etc/opkg/distfeeds.conf
sed -i 's|https://mirrors.tuna.tsinghua.edu.cn|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/opkg/distfeeds.conf

echo "  opkg feeds → mirrors.tuna.tsinghua.edu.cn (HTTP)"

# 保存所有 UCI 变更
echo ""
echo "[保存配置...]"
uci commit switch
uci commit network
uci commit dhcp
uci commit firewall

# 重启网络和防火墙
echo "[重启网络服务...]"
/etc/init.d/network restart &
sleep 5
/etc/init.d/firewall restart &
sleep 2

echo ""
echo "============================================"
echo "  First Boot Setup Complete!"
echo "============================================"
echo ""
echo "  LAN  IP:  192.168.11.1 (Ports 1-3)"
echo "  WAN      : Port0 (DHCP)"
echo "  WiFi SSID: OpenWrt-AP"
echo ""
echo "  Web: http://192.168.11.1"
echo "  SSH: ssh root@192.168.11.1"
echo ""

exit 0
