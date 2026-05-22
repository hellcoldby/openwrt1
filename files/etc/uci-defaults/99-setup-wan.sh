#!/bin/sh
# ============================================================
#  RG100A-BA First Boot Auto Setup (uci-defaults)
#  首次启动时自动执行：WAN 口 + 防火墙
#  执行完毕后自删除
# ============================================================

echo "============================================"
echo "  TIANBEI RG100A-BA - First Boot Setup"
echo "============================================"

# ---- Step 1: Switch VLAN (Port0 → WAN) ----
echo "[1/3] 配置交换机 VLAN (Port0=WAN)..."

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

echo "  ✓ LAN: Ports 1,2,3 | WAN: Port0"

# ---- Step 2: WAN 网络接口 ----
echo "[2/3] 创建 WAN 接口..."

if ! uci -q get network.wan >/dev/null; then
    uci set network.wan=interface
fi
uci set network.wan.device='eth0.2'
uci set network.wan.proto='dhcp'
uci set network.wan.auto='1'

echo "  ✓ WAN = eth0.2 (DHCP)"

# ---- Step 3: 防火墙 ----
echo "[3/3] 配置防火墙..."

# 确保 wan zone 包含 wan 接口
local has_wan=$(uci show firewall | grep -c '@zone\[1\].network=.*wan' || true)
if [ "$has_wan" -eq 0 ]; then
    # 找到 wan zone 并添加
    local wan_zone_idx=$(uci show firewall | grep '\[zone\]' | tail -n 1 | grep -o '\[[0-9]*\]' | tr -d '[]')
    if [ -z "$wan_zone_idx" ]; then
        wan_zone_idx=1
    fi
    uci add_list firewall.@zone[$wan_zone_idx].network='wan'
fi

# 保存所有 UCI 变更
echo ""
echo "[保存配置...]"
uci commit switch
uci commit network
uci commit firewall

# 重启网络和防火墙
echo "[重启网络服务...]"
(/etc/init.d/network restart) &
sleep 5
(/etc/init.d/firewall restart) &
sleep 2

echo ""
echo "============================================"
echo "  ✅ WAN 口配置完成！"
echo "============================================"
echo ""
echo "请将网线插入 Port0（最左边的口）"
echo "等待 DHCP 获取 IP 后即可上网"
echo ""

exit 0
