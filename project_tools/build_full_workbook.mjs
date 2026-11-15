import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

let root = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, ''));
if(path.basename(root)==='project_tools') root=path.dirname(root);
const inv = path.join(root, 'inventory');
const data = JSON.parse(await fs.readFile(path.join(inv, 'workbook_data.json'), 'utf8'));
const wb = Workbook.create();
const C = {navy:'#183B56', teal:'#137C87', ink:'#1D3040', mute:'#596C78', pale:'#F2F7FA', line:'#DCE6EB', green:'#E1F3EA', amber:'#FFF3D9', gray:'#EDF1F4'};

function addSheet(name, title, subtitle, headers, rows, widths, opt={}) {
  const ws = wb.worksheets.add(name);
  const n=headers.length;
  ws.getRange('A1').values=[[title]];
  ws.getRange('A1').format={font:{name:'Aptos Display',size:20,bold:true,color:C.navy},rowHeight:34};
  ws.getRange('A2').values=[[subtitle]];
  ws.getRange('A2').format={font:{name:'Aptos',size:10,color:C.mute},rowHeight:24};
  if(opt.note){
    ws.getRange('A3').values=[[opt.note]];
    ws.getRange('A3').format={font:{name:'Aptos',size:10,color:C.teal},rowHeight:24};
  }
  const matrix=[headers,...rows];
  const grid=ws.getRangeByIndexes(4,0,matrix.length,n);
  grid.values=matrix;
  grid.format={font:{name:'Aptos',size:10,color:C.ink},verticalAlignment:'center',borders:{preset:'all',style:'thin',color:C.line}};
  const head=ws.getRangeByIndexes(4,0,1,n);
  head.format={fill:C.navy,font:{name:'Aptos',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true,verticalAlignment:'center'};
  if(rows.length){
    const body=ws.getRangeByIndexes(5,0,rows.length,n);
    body.format.rowHeight=opt.rowHeight||34;
    body.format.wrapText=true;
    for(let i=0;i<rows.length;i+=2) ws.getRangeByIndexes(5+i,0,1,n).format.fill=C.pale;
  }
  widths.forEach((w,j)=>ws.getRangeByIndexes(0,j,matrix.length+4,1).format.columnWidth=w);
  ws.freezePanes.freezeRows(5);
  return ws;
}

const masterHeaders=[
  'PAHG ID','Symbol / file key','PAHG family name','PAHG year','PAHG taxa','PAHG sequences',
  'Research file source','Inventory status','Raw FASTA','Raw records','Alignment FASTA',
  'Aligned records','Raw/alignment count','Equal alignment lengths','Alignment sites','Tree leaves','ML Newick','NJ Newick',
  'Tree NEXUS','Tree validation','Next action','Function on PAHG','PAHG family page','Online source commit'
];
const masterRows=data.master.map(x=>masterHeaders.map(h=>x[h]));
const master=addSheet('Master inventory','PAHG master inventory',
  '221 official PAHG families  •  3 with your tree files  •  15 with GitHub sequence candidates  •  203 catalogue only',
  masterHeaders,masterRows,
  [11,19,43,13,12,17,19,39,40,14,43,16,19,21,17,15,18,18,16,45,50,70,64,45],
  {note:'IDs come from PAHG family links. All six supplied Newick trees parse and match alignment labels; session review remains.',rowHeight:37});
for(let i=0;i<data.master.length;i++){
  const source=data.master[i]['Research file source'];
  const fill=source==='Your files'?C.green:source==='PAHG GitHub'?C.amber:C.gray;
  master.getRangeByIndexes(5+i,6,1,2).format.fill=fill;
  master.getRangeByIndexes(5+i,0,1,1).format.font={name:'Aptos',size:10,bold:true,color:C.navy};
}

const idBySymbol=new Map(data.master.filter(x=>x['Symbol / file key']).map(x=>[x['Symbol / file key'],x['PAHG ID']]));
const validationByKey=new Map(data.validations.map(x=>[x.family+'|'+x.method,x]));
const treeHeaders=['PAHG ID','Family','Method','MEGA session','Source alignment','Original Newick','Working Newick','Tree leaves','Alignment records','Alignment sites','Equal length','Tree NEXUS','Parse check','Label check','Source comparison','Model','Bootstrap runs','Rates among sites','Gaps / missing data','MEGA version','Release status'];
const treeRows=data.trees.map(t=>{
  const v=validationByKey.get(t.family+'|'+t.method);
  return [
  idBySymbol.get(t.family),t.family,t.method,t.source_session,t.alignment_fasta,t.original_newick,t.working_newick,
  v?.tree_leaves??'',v?.alignment_records??'',v?.alignment_length??'',v?.alignment_equal_length?'YES':'NO',
  t.nexus_tree||'Missing',v?.parse_status||t.parse_validation,v?.label_status||t.label_validation,t.source_comparison,
  t.substitution_model||'Unknown',t.bootstrap_replicates?Number(t.bootstrap_replicates):'Unknown',
  t.rates_among_sites||'Unknown',t.gaps_missing_data||'Unknown',t.mega_version||'Unknown',t.release_status
  ];
});
addSheet('Tree files','Supplied tree records',
  'Six Newick trees from three supplied families; all parse and match their alignment tip labels.',
  treeHeaders,treeRows,[11,13,12,38,40,44,34,15,18,16,16,19,16,16,20,22,19,24,23,19,18],
  {note:'The supplied NEXUS files are alignments. Tree NEXUS conversion and MEGA session comparison remain.',rowHeight:45});

const onlineHeaders=['PAHG ID','File key','PAHG family name','Raw FASTA','Raw records','Alignment FASTA','Aligned records','Same record count','Equal alignment lengths','Review note','Raw URL','Alignment URL','Raw SHA256','Alignment SHA256'];
const onlineRows=data.online.map(o=>{
  const m=data.master.find(x=>x['Symbol / file key']===o.symbol);
  return [m['PAHG ID'],o.symbol,m['PAHG family name'],o.raw_fasta||'Missing',o.raw_records?Number(o.raw_records):'',
    o.alignment_fasta,o.alignment_records?Number(o.alignment_records):'',o.record_count_match,o.alignment_equal_length,
    o.review_note||'Tree source and family linkage require review',o.raw_url,o.alignment_url,o.raw_sha256,o.alignment_sha256];
});
addSheet('Online data','PAHG GitHub file candidates',
  '15 family matches from PAHG public GitHub at a pinned commit; files do not yet establish complete tree datasets.',
  onlineHeaders,onlineRows,[11,14,43,42,15,43,17,21,22,45,68,68,67,67],
  {note:'Record counts may differ because the public raw and aligned files can represent different subsets; investigate before pairing.',rowHeight:44});

const issueHeaders=['PAHG ID','Family','Method','Issue type','What needs attention','Status'];
const issueRows=data.issues.map(o=>[idBySymbol.get(o.family)||'',o.family,o.method||'All',o.severity,o.issue,o.status]);
addSheet('Review log','Review and missing work',
  `${issueRows.length} specific issues and gaps recorded for the files already located.`,
  issueHeaders,issueRows,[11,15,13,15,95,25],{rowHeight:42});

const sourceRows=data.sources.map(s=>[s.source_path,s.snapshot_path,Number(s.bytes),s.sha256]);
addSheet('Original files','Original file manifest',
  `${sourceRows.length} source items recorded in the earlier preservation snapshot. SHA256 identifies each item.`,
  ['Supplied file','Preserved copy','Bytes','SHA256'],sourceRows,[70,70,14,70],{rowHeight:38});

const notes=[
  ['221 PAHG families','Official family table captured on 2026-11-15','https://www.pahgncb.com/genomedb/public/genefamilies'],
  ['3 supplied tree families','SLC4 (ID 1), fibrillar COL (ID 2), ERBB (ID 3)','Family names and links on PAHG match the supplied folder labels'],
  ['15 GitHub candidates','Public FASTA/alignment files matched by names; file relationships need review','https://github.com/PAHG-Database/PAHG/tree/83e0421067465e6855371fb65f99384855d23d80/public'],
  ['203 catalogue-only families','Official names/metadata captured; sequence/alignment/tree source files not located in this project','PAHG family table'],
  ['PAHG sequences','The published count on the PAHG table, separate from local FASTA record counts','PAHG family table'],
  ['Newick file checks','Each supplied tree parses and its leaves match the alignment labels after spaces/underscores are normalized','Tree files sheet'],
  ['Tree NEXUS','The supplied NEXUS files contain alignment blocks, so tree NEXUS exports are missing','Review log'],
  ['Next research step','Create exact NEXUS exports, compare against MEGA sessions, then retrieve original tree sources for remaining families','Research workflow'],
];
addSheet('How to read','How to use this inventory',
  'Family identity, file availability and scientific validation are different questions; this workbook records each separately.',
  ['Item','Meaning','Evidence / source'],notes,[29,93,92],{rowHeight:55});

wb.recalculate();
for(const [sheet,range,file] of [
  ['Master inventory','A1:H13','preview_master.png'],
  ['Tree files','A1:N9','preview_trees.png'],
  ['Online data','A1:J10','preview_online.png'],
  ['Review log','A1:F10','preview_issues.png']
]){
  const rendered=await wb.render({sheetName:sheet,range,scale:1.1,format:'png'});
  await fs.writeFile(path.join(inv,file),new Uint8Array(await rendered.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(inv,'PAHG_master_inventory.xlsx'));
console.log('Exported 221-family workbook');
