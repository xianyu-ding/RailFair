#!/bin/bash
# 快速测试新功能脚本

echo "🧪 测试新功能：票价显示和中间站台"
echo "=================================="
echo ""

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 测试1: 预测API
echo -e "${YELLOW}测试 1: 预测API（包含票价）${NC}"
response=$(curl -s -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "EUS",
    "destination": "MAN",
    "departure_date": "2025-12-25",
    "departure_time": "09:30",
    "include_fares": true
  }')

if echo "$response" | grep -q "prediction"; then
    echo -e "${GREEN}✅ 预测API正常${NC}"
    
    # 检查票价
    advance=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('fares', {}).get('advance', 'null'))" 2>/dev/null)
    offpeak=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('fares', {}).get('off_peak', 'null'))" 2>/dev/null)
    anytime=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('fares', {}).get('anytime', 'null'))" 2>/dev/null)
    
    echo "   票价数据:"
    echo "   - Advance: $advance"
    echo "   - Off-Peak: $offpeak"
    echo "   - Anytime: $anytime"
else
    echo -e "${RED}❌ 预测API失败${NC}"
    echo "$response" | head -5
fi

echo ""

# 测试2: 中间站台API
echo -e "${YELLOW}测试 2: 中间站台API${NC}"
stops_response=$(curl -s http://localhost:8000/api/routes/EUS/MAN/stops)

if echo "$stops_response" | grep -q "stops"; then
    echo -e "${GREEN}✅ 中间站台API正常${NC}"
    
    stop_count=$(echo "$stops_response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('stops', [])))" 2>/dev/null)
    echo "   找到 $stop_count 个站台"
    
    if [ "$stop_count" -gt 0 ]; then
        echo "   前3个站台:"
        echo "$stops_response" | python3 -c "import sys, json; d=json.load(sys.stdin); [print(f\"   - {s.get('location_name', s.get('location'))} ({s.get('location')})\") for s in d.get('stops', [])[:3]]" 2>/dev/null
    fi
else
    echo -e "${RED}❌ 中间站台API失败${NC}"
    echo "$stops_response" | head -5
fi

echo ""
echo -e "${GREEN}测试完成！${NC}"
echo ""
echo "下一步："
echo "1. 打开前端页面: http://localhost:3000"
echo "2. 查询 EUS -> MAN"
echo "3. 检查票价显示（应该显示 '-' 而不是 'Unavailable'）"
echo "4. 点击'查看中间站台'按钮"
echo "5. 验证中间站台列表是否正确显示"
