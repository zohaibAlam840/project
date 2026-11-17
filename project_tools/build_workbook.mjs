import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

let root = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, ''));
if(path.basename(root)==='project_tools') root=path.dirname(root);
const inv = path.join(root, 'inventory');
const data = JSON.parse(await fs.readFile(path.join(inv, 'workbook_data.json'), 'utf8'));
const wb = Workbook.create();
const C = {navy:'#183B56', teal:'#137C87', ink:'#1D3040', mute:'#596C78', pale:'#F2F7FA', line:'#DCE6EB', green:'#E1F3EA', amber:'#FFF3D9', red:'#FBE5E3', gray:'#EDF1F4'};

function addSheet(name, title, subtitle, headers, rows, widths, opt={}) {
  const ws = wb.worksheets.add(name);
  const n=headers.length;
  ws.getRange('A1').values=[[title]];
  ws.getRange('A1').format={font:{name:'Aptos',size:16,bold:true,color:C.navy},rowHeight:32};
  ws.getRange('A2').values=[[subtitle]];
  ws.getRange('A2').format={font:{name:'Aptos',size:10,color:C.mute},rowHeight:24};
  if(opt.note){
    ws.getRange('A3').values=[[opt.note]];
    ws.getRange('A3').format={font:{name:'Aptos',size:10,color:C.teal},rowHeight:24};
  }
  const matrix=[headers,...rows];
  const grid=ws.getRangeByIndexes(4,0,matrix.length,n);
  grid.values=matrix;
  grid.format={font:{name:'Aptos',size:10,color:C.ink},verticalAlignment:'center'};
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
  if(opt.tableName && rows.length){
    let index=n, column='';
    while(index){index--;column=String.fromCharCode(65+(index%26))+column;index=Math.floor(index/26);}
    const table=ws.tables.add(`A5:${column}${5+rows.length}`,true,opt.tableName);
    table.showFilterButton=true;
  }
  return ws;
}

const masterHeaders=[
  'PAHG ID','Symbol / file key','PAHG family name','PAHG year','PAHG taxa','PAHG sequences',
  'Research file source','Inventory status','Raw FASTA','Raw records','Alignment FASTA',
  'Aligned records','Raw/alignment count','Equal alignment lengths','Alignment sites','Shortest aligned record',
  'Source limit flag','Header line breaks repaired','Raw sequences found in alignment','Tree leaves','ML Newick','NJ Newick',
  'Tree NEXUS','Tree validation','Next action','Function on PAHG','PAHG family page','Online source commit','Working FASTA path',
  'GitHub source evidence','Official alignment issues','Official raw issues','Official raw SHA256','Official alignment SHA256'
];
const masterRows=data.master.map(x=>masterHeaders.map(h=>x[h]));
const summaryRows=[
  ['Official PAHG families',data.summary.catalogue_families,'One tracked row per official PAHG family ID'],
  ['Official FASTAs captured',data.summary.official_fasta_files,'Raw sequence and alignment download for every family'],
  ['Source alignments incomplete',data.summary.official_incomplete_alignments,'Final aligned record is shorter than preceding records'],
  ['Format or pairing review',data.summary.official_pairing_review,'Equal-length alignment with raw/published count or sequence discrepancy'],
  ['Sequence checks pass',data.summary.official_sequence_checks_pass,'Alignment, raw sequences and published count agree; PAHG tree downloads unavailable'],
  ['Supplied tree families',data.summary.user_file_families,'Six ML/NJ Newick trees parse; MEGA comparison still pending'],
  ['GitHub FASTAs verified',data.summary.public_fastas_verified,'Every file matches the pinned PAHG Git blob'],
  ['Official header breaks repaired',data.summary.official_header_repairs,'Working copies only; original downloads preserved'],
  ['GitHub header breaks repaired',data.summary.public_fasta_header_repairs,'Working copies only; original repository files preserved'],
];
addSheet('Status summary','PAHG data cleaning status',
  'All 221 families have official sequence and alignment downloads; each has an evidence-based status.',
  ['Measure','Count','What it means'],summaryRows,[39,15,95],
  {note:'Even sequence checks passing does not verify a published ML/NJ tree or its MEGA settings.',rowHeight:39,tableName:'PAHGStatus'});
const master=addSheet('Master inventory','PAHG master inventory',
  `221 official families  •  121 incomplete source alignments  •  32 pairing reviews  •  68 sequence checks pass`,
  masterHeaders,masterRows,
  [11,19,43,13,12,17,23,43,40,14,43,16,19,21,17,20,17,21,23,15,18,18,16,45,50,70,64,45,60,28,70,70,68,68],
  {note:'Filter Inventory status. The 3 supplied tree families lead; all other rows use official PAHG downloads.',rowHeight:37,tableName:'PAHGMaster'});
for(let i=0;i<data.master.length;i++){
  const source=data.master[i]['Research file source'];
  const status=data.master[i]['Inventory status'];
  const fill=status==='SOURCE ALIGNMENT INCOMPLETE'?C.red:status==='FORMAT OR PAIRING REVIEW'?C.amber:status==='SEQUENCE CHECKS PASS; PAHG TREE DOWNLOAD UNAVAILABLE'||source==='Your files'?C.green:C.gray;
  master.getRangeByIndexes(5+i,6,1,2).format.fill=fill;
  master.getRangeByIndexes(5+i,0,1,1).format.font={name:'Aptos',size:10,bold:true,color:C.navy};
}

const idBySymbol=new Map(data.master.filter(x=>x['Symbol / file key']).map(x=>[x['Symbol / file key'],x['PAHG ID']]));
const validationByKey=new Map(data.validations.map(x=>[x.family+'|'+x.method,x]));
const conversionByKey=new Map(data.conversions.map(x=>[x.family+'|'+x.method,x]));
const treeHeaders=['PAHG ID','Family','Method','MEGA session','Source alignment','Original Newick','Working Newick','Tree leaves','Alignment records','Alignment sites','Equal length','Tree NEXUS file','NEXUS round trip','Parse check','Label check','Branch review','MEGA metadata','MEGA tree comparison','Model','Bootstrap runs','Rates among sites','Gaps / missing data','MEGA version','Release status'];
const treeRows=data.trees.map(t=>{
  const v=validationByKey.get(t.family+'|'+t.method);
  const c=conversionByKey.get(t.family+'|'+t.method);
  return [
  idBySymbol.get(t.family),t.family,t.method,t.source_session,t.alignment_fasta,t.original_newick,t.working_newick,
  v?.tree_leaves??'',v?.alignment_records??'',v?.alignment_length??'',v?.alignment_equal_length?'YES':'NO',
  c?.nexus_tree?.split('/').at(-1)||'Missing',c?.nexus_roundtrip||'Pending',v?.parse_status||t.parse_validation,v?.label_status||t.label_validation,
  c?.negative_branch_count?`${c.negative_branch_count} negative branch`:'None found',c?.session_metadata||'Pending',c?.session_tree_comparison||'PENDING',
  t.substitution_model||'Unknown',t.bootstrap_replicates?Number(t.bootstrap_replicates):'Unknown',
  t.rates_among_sites||'Unknown',t.gaps_missing_data||'Unknown',t.mega_version||'Unknown',t.release_status
  ];
});
const treeSheet=addSheet('Tree files','Supplied tree records',
  'Six exact NEXUS tree copies parse and match the Newick trees; one negative NJ branch requires review.',
  treeHeaders,treeRows,[11,13,12,38,40,44,34,15,18,16,16,38,19,16,16,23,19,23,22,19,24,23,19,18],
  {note:'The original supplied .nex files are alignments. Separate NEXUS tree files are in working_copies; MEGA topology comparison remains.',rowHeight:45,tableName:'PAHGTrees'});
data.trees.forEach((t,i)=>{
  if(conversionByKey.get(t.family+'|'+t.method)?.negative_branch_count) treeSheet.getRangeByIndexes(5+i,15,1,1).format.fill=C.amber;
});

const onlineAudit=new Map(data.online_audit.map(o=>[o.symbol,o]));
const onlineHeaders=['PAHG ID','File key','PAHG family name','Raw FASTA','Raw records','Alignment FASTA','Aligned records','Shortest sequence','Longest sequence','Equal lengths','Source limit flag','Exact sequence matches','Readiness','Review note','Raw URL','Alignment URL','Raw SHA256','Alignment SHA256'];
const onlineRows=data.online.map(o=>{
  const m=data.master.find(x=>x['Symbol / file key']===o.symbol);
  const a=onlineAudit.get(o.symbol);
  return [m['PAHG ID'],o.symbol,m['PAHG family name'],o.raw_fasta||'Missing',o.raw_records?Number(o.raw_records):'',
    o.alignment_fasta,a.alignment_records,a.alignment_sites_min,a.alignment_sites_max,a.equal_alignment_lengths,
    a.possible_source_truncation,a.exact_ungapped_sequence_matches,a.readiness,
    a.review_note||'Tree source and family linkage require review',o.raw_url,o.alignment_url,o.raw_sha256,o.alignment_sha256];
});
addSheet('Online data','PAHG GitHub file candidates',
  '15 name-matched alignments from the pinned public commit; ten fail equal-length checks.',
  onlineHeaders,onlineRows,[11,14,43,42,15,43,17,19,19,17,18,21,37,62,68,68,67,67],
  {note:'Exact sequence matches compare raw proteins with ungapped aligned proteins; labels often differ.',rowHeight:44,tableName:'PAHGOnline'});

const officialHeaders=['PAHG ID','PAHG family name','Published sequences','Raw records','Aligned records','Equal lengths','Shortest sequence','Longest sequence','Raw matches in alignment','Count difference','Status','Alignment issue','Raw issue','Header breaks repaired','Official raw file','Official alignment file','Raw SHA256','Alignment SHA256'];
const officialRows=data.live_audit.map(a=>[a.pahg_id,a.family_name,a.published_sequence_count,a.raw_records,a.alignment_records,
  a.alignment_equal_lengths,a.alignment_min_length,a.alignment_max_length,a.exact_ungapped_sequence_matches,
  a.alignment_vs_published_count,a.inventory_status,a.alignment_issues||'',a.raw_issues||'',
  a.alignment_header_repairs+a.raw_header_repairs,a.raw_working_path,a.alignment_working_path,
  a.raw_sha256,a.alignment_sha256]);
addSheet('Official downloads','Official PAHG file audit',
  'Both downloads captured for every family; 68 pass sequence checks and 121 source alignments are incomplete.',
  officialHeaders,officialRows,[11,45,20,15,19,17,19,19,23,19,43,77,65,20,70,70,68,68],
  {note:'Sequence checks require equal lengths, matching published and raw counts, and exact ungapped protein matches.',rowHeight:42,tableName:'PAHGOfficial'});

const pairingHeaders=['PAHG ID','Family','Published','Raw','Aligned','Exact matches','Raw unmatched','Aligned unmatched','Unmatched raw labels','Unmatched aligned labels','Raw format issue'];
const pairingRows=data.pairing_review.map(r=>[r.pahg_id,r.family_name,r.published_count,r.raw_records,r.aligned_records,
  r.exact_sequence_matches,r.raw_unmatched_count,r.aligned_unmatched_count,
  r.raw_unmatched_headers.join(' | '),r.aligned_unmatched_headers.join(' | '),r.raw_format_issue||'']);
addSheet('Pairing review','Records requiring pairing review',
  '32 equal-length datasets with a count, exact-sequence or raw-format discrepancy.',
  pairingHeaders,pairingRows,[11,43,15,14,16,19,19,21,95,95,55],
  {note:'Unmatched labels locate records to inspect; no source sequence was silently deleted or changed.',rowHeight:58,tableName:'PAHGPairing'});

const normByName=new Map(data.normalization.map(x=>[x.filename,x]));
const auditHeaders=['Public FASTA','Kind','Source bytes','Records','Equal lengths','Shortest record','Longest record','Embedded headers','Source limit flag','Issue','Working copy','Source SHA256'];
const auditRows=data.public_audit.map(a=>{
  const n=normByName.get(a.filename);
  return [a.filename,a.kind,a.bytes,n.working_records,a.equal_lengths,a.min_length,a.max_length,
    n.inserted_header_line_breaks,a.possible_65535_truncation,a.issues||'No format issue detected',n.working_path,a.sha256];
});
addSheet('Public file audit','All public FASTA files',
  '93 GitHub files verified against the pinned commit; working copies preserve every sequence character.',
  auditHeaders,auditRows,[49,15,16,13,18,18,18,18,18,75,70,68],
  {note:'A format pass is not proof that the file matches a published PAHG analysis.',rowHeight:42,tableName:'PAHGPublicAudit'});

const issueHeaders=['PAHG ID','Family','Method','Issue type','What needs attention','Status'];
const issueRows=data.issues.map(o=>[idBySymbol.get(o.family)||'',o.family,o.method||'All',o.severity,o.issue,o.status]);
addSheet('Review log','Review and missing work',
  `${issueRows.length} specific issues and gaps recorded for the files already located.`,
  issueHeaders,issueRows,[11,15,13,15,95,25],{rowHeight:42,tableName:'PAHGReview'});

const sourceRows=data.sources.map(s=>[s.source_path,s.snapshot_path,Number(s.bytes),s.sha256]);
addSheet('Original files','Original file manifest',
  `${sourceRows.length} source items recorded in the earlier preservation snapshot. SHA256 identifies each item.`,
  ['Supplied file','Preserved copy','Bytes','SHA256'],sourceRows,[70,70,14,70],{rowHeight:38,tableName:'PAHGOriginals'});

const notes=[
  ['221 PAHG families','Official family table captured on 2026-11-15','https://www.pahgncb.com/genomedb/public/genefamilies'],
  ['3 supplied tree families','SLC4 (ID 1), fibrillar COL (ID 2), ERBB (ID 3)','Family names and links on PAHG match the supplied folder labels'],
  ['442 official FASTAs','One raw and one alignment download captured per family','https://www.pahgncb.com/genomedb/public/downloads'],
  ['121 incomplete alignments','120 have a shortened final record; one ends at the source limit with missing records','Official downloads'],
  ['32 pairing reviews','Equal-length alignment, but published count or raw-sequence consistency requires review','Official downloads'],
  ['68 sequence checks pass','Raw/aligned sequence multisets and counts agree; PAHG tree downloads unavailable','Official downloads'],
  ['Header repairs','28 GitHub and 12 official header breaks repaired in working copies; originals preserved','Public file audit and Official downloads'],
  ['65,535-byte limit','113 official alignments are exactly 65,535 bytes; ABLIM equals the GitHub copy after line-ending normalization','Official downloads'],
  ['PAHG sequences','The published count on the PAHG table, separate from local FASTA record counts','PAHG family table'],
  ['Newick file checks','Each supplied tree parses and its leaves match the alignment labels after spaces/underscores are normalized','Tree files sheet'],
  ['Tree NEXUS','Six separate NEXUS tree files wrap the exact supplied Newick expressions; all pass independent parser round trips','Tree files sheet'],
  ['Negative branch','The COL NJ tree has one small negative branch length, preserved exactly and flagged for scientific review','Review log'],
  ['Next research step','Obtain complete original alignments and ML/NJ trees; compare six supplied trees with MEGA','Research workflow'],
];
addSheet('How to read','How to use this inventory',
  'Family identity, file availability and scientific validation are different questions; this workbook records each separately.',
  ['Item','Meaning','Evidence / source'],notes,[29,93,92],{rowHeight:55});

wb.recalculate();
for(const [sheet,range,file] of [
  ['Status summary','A1:C16','preview_status.png'],
  ['Master inventory','A1:H13','preview_master.png'],
  ['Tree files','A1:N9','preview_trees.png'],
  ['Online data','A1:J10','preview_online.png'],
  ['Official downloads','A1:K10','preview_official.png'],
  ['Pairing review','A1:H10','preview_pairing.png'],
  ['Review log','A1:F10','preview_issues.png']
]){
  const rendered=await wb.render({sheetName:sheet,range,scale:1.1,format:'png'});
  await fs.writeFile(path.join(inv,file),new Uint8Array(await rendered.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(inv,'PAHG_master_inventory.xlsx'));
const outputDir=path.join(root,'outputs','2026-11-18-data-cleaning');
await fs.mkdir(outputDir,{recursive:true});
await fs.copyFile(path.join(inv,'PAHG_master_inventory.xlsx'),path.join(outputDir,'PAHG_master_inventory.xlsx'));
console.log('Exported 221-family workbook');
