#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// 读取命令行参数
const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
  console.error('Usage: node ua-tour-analyze.js <input-json> <output-json>');
  process.exit(1);
}

// 读取输入文件
let inputData;
try {
  inputData = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
} catch (err) {
  console.error(`Failed to read input file: ${err.message}`);
  process.exit(1);
}

const nodes = inputData.nodes || [];
const edges = inputData.edges || [];
const layers = inputData.layers || [];

// 构建邻接表
const inEdges = new Map();  // node -> incoming edges
const outEdges = new Map(); // node -> outgoing edges

nodes.forEach(node => {
  inEdges.set(node.id, []);
  outEdges.set(node.id, []);
});

edges.forEach(edge => {
  if (inEdges.has(edge.target)) {
    inEdges.get(edge.target).push(edge);
  }
  if (outEdges.has(edge.source)) {
    outEdges.get(edge.source).push(edge);
  }
});

// A. Fan-In Ranking (重要性)
const fanInRanking = nodes
  .map(node => ({
    id: node.id,
    fanIn: inEdges.get(node.id).length,
    name: node.name,
    summary: node.summary,
    type: node.type
  }))
  .sort((a, b) => b.fanIn - a.fanIn)
  .slice(0, 20);

// B. Fan-Out Ranking (范围)
const fanOutRanking = nodes
  .map(node => ({
    id: node.id,
    fanOut: outEdges.get(node.id).length,
    name: node.name,
    summary: node.summary,
    type: node.type
  }))
  .sort((a, b) => b.fanOut - a.fanOut)
  .slice(0, 20);

// 计算fan-in和fan-out的统计值用于后续评分
const fanInValues = Array.from(inEdges.values()).map(e => e.length);
const fanOutValues = Array.from(outEdges.values()).map(e => e.length);
const fanInThreshold = Math.max(...fanInValues) * 0.9; // top 10%
const fanOutTopThreshold = Math.max(...fanOutValues) * 0.9; // top 10%
const fanInBottomThreshold = fanInValues.sort((a, b) => a - b)[Math.floor(fanInValues.length * 0.25)]; // bottom 25%

// C. Entry Point Candidates
const entryPointScores = new Map();

nodes.forEach(node => {
  let score = 0;
  const filename = node.name || '';
  const filePath = node.filePath || '';

  // 代码文件评分规则
  if (node.type === 'file') {
    // 入口文件名
    if (filename === '__init__.py') {
      score += 3;
    }
    if (filename === 'main.py' || filename === 'app.py' || filename === 'server.py' || filename === 'index.ts' || filename === 'index.js') {
      score += 3;
    }
    // 文件深度（根目录或一级）
    const depth = (filePath.match(/\//g) || []).length;
    if (depth <= 1) {
      score += 1;
    }
    // 高fan-out（top 10%）
    const fanOut = outEdges.get(node.id).length;
    if (fanOut >= fanOutTopThreshold) {
      score += 1;
    }
    // 低fan-in（bottom 25%）
    const fanIn = inEdges.get(node.id).length;
    if (fanIn <= fanInBottomThreshold) {
      score += 1;
    }
  }

  // 文档文件评分规则
  if (node.type === 'document') {
    if (filename === 'README.md' && depth === 0) {
      score += 5;
    } else if (filename.endsWith('.md') && depth <= 1) {
      score += 2;
    }
  }

  if (score > 0) {
    entryPointScores.set(node.id, {
      id: node.id,
      score: score,
      name: node.name,
      summary: node.summary,
      type: node.type,
      filePath: node.filePath
    });
  }
});

const entryPointCandidates = Array.from(entryPointScores.values())
  .sort((a, b) => b.score - a.score)
  .slice(0, 5);

// D. BFS Traversal (从入口点开始)
// 找到代码入口点（排除文档）
const codeEntryPoints = entryPointCandidates.filter(ep => ep.type === 'file');
const startNode = codeEntryPoints.length > 0 ? codeEntryPoints[0].id :
                  (entryPointCandidates.length > 0 ? entryPointCandidates[0].id : nodes[0].id);

const bfsOrder = [];
const depthMap = new Map();
const visited = new Set();
const queue = [{node: startNode, depth: 0}];

visited.add(startNode);

while (queue.length > 0) {
  const {node, depth} = queue.shift();
  bfsOrder.push(node);
  depthMap.set(node, depth);

  // 只跟随imports和calls边
  const outgoing = outEdges.get(node) || [];
  const relevantEdges = outgoing.filter(e =>
    e.type === 'imports' || e.type === 'calls'
  );

  for (const edge of relevantEdges) {
    if (!visited.has(edge.target)) {
      visited.add(edge.target);
      queue.push({node: edge.target, depth: depth + 1});
    }
  }
}

// 按深度分组
const byDepth = {};
depthMap.forEach((depth, node) => {
  if (!byDepth[depth]) {
    byDepth[depth] = [];
  }
  byDepth[depth].push(node);
});

// E. Non-Code Files Inventory
const nonCodeFiles = {
  documentation: [],
  infrastructure: [],
  data: [],
  config: []
};

nodes.forEach(node => {
  if (node.type === 'document') {
    nonCodeFiles.documentation.push({
      id: node.id,
      name: node.name,
      summary: node.summary
    });
  } else if (node.type === 'service' || node.type === 'pipeline') {
    nonCodeFiles.infrastructure.push({
      id: node.id,
      name: node.name,
      summary: node.summary
    });
  } else if (node.type === 'table' || node.type === 'schema' || node.type === 'endpoint') {
    nonCodeFiles.data.push({
      id: node.id,
      name: node.name,
      summary: node.summary
    });
  } else if (node.type === 'config') {
    nonCodeFiles.config.push({
      id: node.id,
      name: node.name,
      summary: node.summary
    });
  }
});

// F. Tightly Coupled Clusters
// 找出双向关系（A->B and B->A）
const bidirectionalPairs = [];
const edgeSet = new Set(edges.map(e => `${e.source}|${e.target}`));

edges.forEach(edge => {
  if ((edge.type === 'imports' || edge.type === 'calls') &&
      edgeSet.has(`${edge.target}|${edge.source}`)) {
    bidirectionalPairs.push([edge.source, edge.target]);
  }
});

// 构建簇
const clusters = [];
const visitedNodes = new Set();

bidirectionalPairs.forEach(pair => {
  if (visitedNodes.has(pair[0]) || visitedNodes.has(pair[1])) return;

  const cluster = new Set(pair);
  let added = true;

  while (added) {
    added = false;
    for (const node of nodes) {
      if (cluster.has(node.id)) continue;

      // 计算该节点与簇中节点的连接数
      let connections = 0;
      for (const clusterNode of cluster) {
        if (edgeSet.has(`${node.id}|${clusterNode}`) || edgeSet.has(`${clusterNode}|${node.id}`)) {
          connections++;
        }
      }

      if (connections >= 2) {
        cluster.add(node.id);
        added = true;
      }
    }
  }

  if (cluster.size >= 2) {
    const clusterNodes = Array.from(cluster);
    clusterNodes.forEach(n => visitedNodes.add(n));

    // 计算簇内部的边数
    let edgeCount = 0;
    clusterNodes.forEach(a => {
      clusterNodes.forEach(b => {
        if (a !== b && edgeSet.has(`${a}|${b}`)) {
          edgeCount++;
        }
      });
    });

    clusters.push({
      nodes: clusterNodes,
      edgeCount: edgeCount
    });
  }
});

// 取top 5-10个簇
clusters.sort((a, b) => b.edgeCount - a.edgeCount);
const topClusters = clusters.slice(0, 10);

// G. Layer List
const layersOutput = {
  count: layers.length,
  list: layers.map(l => ({
    id: l.id,
    name: l.name,
    description: l.description
  }))
};

// H. Node Summary Index
const nodeSummaryIndex = {};
nodes.forEach(node => {
  nodeSummaryIndex[node.id] = {
    name: node.name,
    type: node.type,
    summary: node.summary || '',
    filePath: node.filePath || ''
  };
});

// 输出结果
const output = {
  scriptCompleted: true,
  entryPointCandidates: entryPointCandidates.map(ep => ({
    id: ep.id,
    score: ep.score,
    name: ep.name,
    summary: ep.summary
  })),
  fanInRanking: fanInRanking,
  fanOutRanking: fanOutRanking,
  bfsTraversal: {
    startNode: startNode,
    order: bfsOrder,
    depthMap: Object.fromEntries(depthMap),
    byDepth: byDepth
  },
  nonCodeFiles: nonCodeFiles,
  clusters: topClusters,
  layers: layersOutput,
  nodeSummaryIndex: nodeSummaryIndex,
  totalNodes: nodes.length,
  totalEdges: edges.length
};

fs.writeFileSync(outputFile, JSON.stringify(output, null, 2));
console.log(`Analysis complete. Results written to ${outputFile}`);
process.exit(0);