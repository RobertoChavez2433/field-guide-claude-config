import 'dart:convert';
import 'dart:io';

import 'package:construction_inspector/features/contractors/data/models/contractor.dart';
import 'package:construction_inspector/features/contractors/data/models/equipment.dart';
import 'package:construction_inspector/features/contractors/data/models/entry_personnel.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/forms/data/models/form_response.dart';
import 'package:construction_inspector/features/forms/data/models/inspector_form.dart';
import 'package:construction_inspector/features/forms/data/pdf/mdot_0582b_pdf_filler.dart';
import 'package:construction_inspector/features/forms/data/pdf/mdot_1126_pdf_filler.dart';
import 'package:construction_inspector/features/forms/data/pdf/mdot_1174r_pdf_filler.dart';
import 'package:construction_inspector/features/forms/data/registries/form_pdf_filler_registry.dart';
import 'package:construction_inspector/features/forms/data/registries/form_type_constants.dart';
import 'package:construction_inspector/features/forms/data/services/form_pdf_service.dart';
import 'package:construction_inspector/features/photos/data/models/photo.dart';
import 'package:construction_inspector/features/pdf/services/pdf_service.dart';
import 'package:construction_inspector/features/projects/data/models/project.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/quantities/data/models/entry_quantity.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('writes PDF fidelity verification artifacts', () async {
    final outputRoot = Directory(
      '.codex/artifacts/2026-04-10/pdf_fidelity_verification',
    );
    final sourceDir = Directory('${outputRoot.path}/source');
    final referenceDir = Directory('${outputRoot.path}/reference_filled');
    final generatedDir = Directory('${outputRoot.path}/generated');
    sourceDir.createSync(recursive: true);
    referenceDir.createSync(recursive: true);
    generatedDir.createSync(recursive: true);

    final fillerRegistry = FormPdfFillerRegistry.instance;
    fillerRegistry.register(kFormTypeMdot0582b, fillMdot0582bPdfFields);
    fillerRegistry.register(kFormTypeMdot1126, fillMdot1126PdfFields);
    fillerRegistry.register(kFormTypeMdot1174r, fillMdot1174rPdfFields);

    final formPdfService = FormPdfService();
    final idrPdfService = PdfService();

    const original0582bPath =
        r'C:\Users\rseba\OneDrive\Desktop\DEBUG_mdot_0582b_density.pdf';
    const original1174rPath =
        r'C:\Users\rseba\OneDrive\Desktop\DEBUG_mdot_1174r_concrete.pdf';

    final original0582b = File(original0582bPath);
    final original1174r = File(original1174rPath);
    expect(original0582b.existsSync(), isTrue, reason: original0582bPath);
    expect(original1174r.existsSync(), isTrue, reason: original1174rPath);

    await _copyFile(
      original0582b,
      '${sourceDir.path}/original_0582b_density.pdf',
    );
    await _copyFile(
      original1174r,
      '${sourceDir.path}/original_1174r_concrete.pdf',
    );
    await _copyAsset(
      kFormTemplateMdot0582b,
      '${sourceDir.path}/template_shipped_0582b.pdf',
    );
    await _copyAsset(
      kFormTemplateMdot1174r,
      '${sourceDir.path}/template_shipped_1174r.pdf',
    );
    await _copyAsset(
      kFormTemplateMdot1126,
      '${sourceDir.path}/template_shipped_1126.pdf',
    );
    await _copyAsset(
      'assets/templates/idr_template.pdf',
      '${sourceDir.path}/template_shipped_idr.pdf',
    );

    await _writePdf(
      '${referenceDir.path}/reference_original_0582b_debug_all_text_fields.pdf',
      await formPdfService.generateDebugPdf(
        InspectorForm(
          id: 'debug-original-0582b',
          name: 'Original 0582B Debug Reference',
          templatePath: original0582bPath,
          templateSource: TemplateSource.file,
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_original_1174r_debug_all_text_fields.pdf',
      await formPdfService.generateDebugPdf(
        InspectorForm(
          id: 'debug-original-1174r',
          name: 'Original 1174R Debug Reference',
          templatePath: original1174rPath,
          templateSource: TemplateSource.file,
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_original_0582b_business_values.pdf',
      await formPdfService.generateFormPdf(
        FormPdfData(
          response: _build0582bResponse(),
          form: InspectorForm(
            id: 'original-0582b-business-values',
            name: 'Original 0582B Business Values Reference',
            templatePath: original0582bPath,
            templateSource: TemplateSource.file,
          ),
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_original_1174r_business_values.pdf',
      await formPdfService.generateFormPdf(
        FormPdfData(
          response: _build1174rResponse(),
          form: InspectorForm(
            id: 'original-1174r-business-values',
            name: 'Original 1174R Business Values Reference',
            templatePath: original1174rPath,
            templateSource: TemplateSource.file,
          ),
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_shipped_0582b_debug_all_text_fields.pdf',
      await formPdfService.generateDebugPdf(
        InspectorForm(
          id: kFormTypeMdot0582b,
          name: 'MDOT 0582B Density',
          templatePath: kFormTemplateMdot0582b,
          templateSource: TemplateSource.asset,
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_shipped_1174r_debug_all_text_fields.pdf',
      await formPdfService.generateDebugPdf(
        InspectorForm(
          id: kFormTypeMdot1174r,
          name: 'MDOT 1174R Concrete',
          templatePath: kFormTemplateMdot1174r,
          templateSource: TemplateSource.asset,
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_shipped_1126_debug_all_text_fields.pdf',
      await formPdfService.generateDebugPdf(
        InspectorForm(
          id: kFormTypeMdot1126,
          name: 'MDOT 1126 Weekly SESC',
          templatePath: kFormTemplateMdot1126,
          templateSource: TemplateSource.asset,
        ),
      ),
    );
    await _writePdf(
      '${referenceDir.path}/reference_shipped_idr_debug_all_text_fields.pdf',
      await idrPdfService.generateDebugPdf(),
    );

    await _writePdf(
      '${generatedDir.path}/generated_0582b_business_values.pdf',
      await formPdfService.generateFormPdf(
        FormPdfData(
          response: _build0582bResponse(),
          form: InspectorForm(
            id: kFormTypeMdot0582b,
            name: 'MDOT 0582B Density',
            templatePath: kFormTemplateMdot0582b,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/generated_1174r_business_values.pdf',
      await formPdfService.generateFormPdf(
        FormPdfData(
          response: _build1174rResponse(),
          form: InspectorForm(
            id: kFormTypeMdot1174r,
            name: 'MDOT 1174R Concrete',
            templatePath: kFormTemplateMdot1174r,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/generated_1126_business_values.pdf',
      await formPdfService.generateFormPdf(
        FormPdfData(
          response: _build1126Response(),
          form: InspectorForm(
            id: kFormTypeMdot1126,
            name: 'MDOT 1126 Weekly SESC',
            templatePath: kFormTemplateMdot1126,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/generated_idr_business_values.pdf',
      await idrPdfService.generateIdrPdf(_buildIdrData()),
    );
    await _writePdf(
      '${generatedDir.path}/preview_0582b_business_values_read_only.pdf',
      await formPdfService.generatePreviewPdf(
        FormPdfData(
          response: _build0582bResponse(),
          form: InspectorForm(
            id: kFormTypeMdot0582b,
            name: 'MDOT 0582B Density',
            templatePath: kFormTemplateMdot0582b,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/preview_1174r_business_values_read_only.pdf',
      await formPdfService.generatePreviewPdf(
        FormPdfData(
          response: _build1174rResponse(),
          form: InspectorForm(
            id: kFormTypeMdot1174r,
            name: 'MDOT 1174R Concrete',
            templatePath: kFormTemplateMdot1174r,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/preview_1126_business_values_read_only.pdf',
      await formPdfService.generatePreviewPdf(
        FormPdfData(
          response: _build1126Response(),
          form: InspectorForm(
            id: kFormTypeMdot1126,
            name: 'MDOT 1126 Weekly SESC',
            templatePath: kFormTemplateMdot1126,
            templateSource: TemplateSource.asset,
          ),
        ),
      ),
    );
    await _writePdf(
      '${generatedDir.path}/preview_idr_business_values_read_only.pdf',
      await idrPdfService.generatePreviewPdf(_buildIdrData()),
    );

    final manifest = <String, Object?>{
      'generated_at': DateTime.now().toIso8601String(),
      'output_root': outputRoot.path.replaceAll('\\', '/'),
      'required_gate': 'original-acroform-pdf-fidelity',
      'artifacts': <String, Object?>{
        'source': <String>[
          'source/original_0582b_density.pdf',
          'source/original_1174r_concrete.pdf',
          'source/template_shipped_0582b.pdf',
          'source/template_shipped_1174r.pdf',
          'source/template_shipped_1126.pdf',
          'source/template_shipped_idr.pdf',
        ],
        'reference_filled': <String>[
          'reference_filled/reference_original_0582b_debug_all_text_fields.pdf',
          'reference_filled/reference_original_1174r_debug_all_text_fields.pdf',
          'reference_filled/reference_original_0582b_business_values.pdf',
          'reference_filled/reference_original_1174r_business_values.pdf',
          'reference_filled/reference_shipped_0582b_debug_all_text_fields.pdf',
          'reference_filled/reference_shipped_1174r_debug_all_text_fields.pdf',
          'reference_filled/reference_shipped_1126_debug_all_text_fields.pdf',
          'reference_filled/reference_shipped_idr_debug_all_text_fields.pdf',
        ],
        'generated': <String>[
          'generated/generated_0582b_business_values.pdf',
          'generated/generated_1174r_business_values.pdf',
          'generated/generated_1126_business_values.pdf',
          'generated/generated_idr_business_values.pdf',
          'generated/preview_0582b_business_values_read_only.pdf',
          'generated/preview_1174r_business_values_read_only.pdf',
          'generated/preview_1126_business_values_read_only.pdf',
          'generated/preview_idr_business_values_read_only.pdf',
        ],
      },
      'mdot_0582b_user_inputs': <String, String>{
        'BRow1_moisture_percent': '8',
        'CRow1_volume_mold_cuft': '.0439',
        'DRow1_wet_soil_mold_g': '4600',
        'ERow1_mold_g': '2006',
      },
      'mdot_0582b_expected_autofill': <String, String>{
        'FRow1': '2594',
        'GRow1': '5.72',
        'HRow1': '130.2',
      },
    };
    final manifestFile = File('${outputRoot.path}/manifest.json');
    await manifestFile.writeAsString(
      const JsonEncoder.withIndent('  ').convert(manifest),
    );
  });
}

Future<void> _copyFile(File source, String targetPath) async {
  final target = File(targetPath);
  await source.copy(target.path);
}

Future<void> _copyAsset(String assetPath, String targetPath) async {
  final bytes = await rootBundle.load(assetPath);
  await _writePdf(targetPath, bytes.buffer.asUint8List());
}

Future<void> _writePdf(String targetPath, Uint8List bytes) async {
  final file = File(targetPath);
  await file.parent.create(recursive: true);
  await file.writeAsBytes(bytes, flush: true);
}

FormResponse _build0582bResponse() {
  return FormResponse(
    id: 'resp-0582b-pdf-fidelity',
    projectId: 'proj-0582b',
    formType: kFormTypeMdot0582b,
    headerData: jsonEncode({
      'date': '2026-04-10',
      'control_section_id': 'CS-0582',
      'job_number': 'JOB-0582',
      'route_street': 'M-43',
      'gauge_number': 'G-582',
      'inspector': 'Inspector Real',
      'cert_number': 'CERT-582',
      'phone': '555-0582',
      'construction_eng': 'Engineer One',
      'asst_eng': 'Engineer Two',
    }),
    responseData: jsonEncode({
      'test_rows': [
        {
          'test_number': '1',
          'is_recheck': 'false',
          'test_depth_in': '6',
          'counts_mc': '2450',
          'counts_dc': '1820',
          'dry_density_pcf': '121.4',
          'wet_density_pcf': '129.4',
          'moisture_pcf': '8.8',
          'moisture_percent': '8.0',
          'max_density_pcf': '132.0',
          'percent_compaction': '99.4',
          'station': '10+50',
          'distance_left_ft': '4',
          'distance_right_ft': '2',
          'depth_below_grade_ft': '1.0',
          'item_of_work': 'Aggregate base',
        },
      ],
      'proctor_rows': [
        {
          'test_number': '1',
          'moisture_percent': '8',
          'volume_mold_cuft': '.0439',
          'wet_soil_mold_g': '4600',
          'mold_g': '2006',
          'max_density_pcf': '132.0',
          'optimum_moisture_pct': '8.0',
          'weights_20_10': ['4600', '4602'],
        },
      ],
      'chart_standards': {
        'density_first': '131.5',
        'density_second': '132.5',
        'moisture_first': '7.5',
        'moisture_second': '8.5',
      },
      'operating_standards': {'density': '130.0', 'moisture': '7.5'},
      'remarks': 'Verification artifact built against original PDF contract.',
    }),
  );
}

FormResponse _build1174rResponse() {
  return FormResponse(
    id: 'resp-1174r-pdf-fidelity',
    projectId: 'proj-1174r',
    formType: kFormTypeMdot1174r,
    headerData: jsonEncode({'route': 'M-53'}),
    responseData: jsonEncode({
      'contractor_name': 'Prime Concrete',
      'project_name': 'US-31 Bridge Rehab',
      'subcontractor_name': 'Finish Crew',
      'control_section_job_number': 'CS-7 / JOB-9',
      'concrete_supplier': 'Great Lakes Ready Mix',
      'route': 'M-53',
      'maximum_time': '90 min',
      'structure_number': 'B-100',
      'weather_am': 'Clear',
      'weather_pm': 'Cloudy',
      'report_number': '1174-7',
      'report_date': '2026-04-09',
      'max_water_added_per_cyd': '5',
      'water_added_reason': 'Workability',
      'beams_cylinders_made': '4 beams / 6 cylinders',
      'curing_compound_used_gallons': '12',
      'intended_air_min': '5',
      'intended_air_max': '8',
      'intended_slump_min': '2',
      'intended_slump_max': '4',
      'air_slump_pairs': [
        {
          'left_time': '08:15',
          'left_atmosphere': '52',
          'left_concrete': '65',
          'left_air_content': '6.0',
          'left_slump': '3',
          'left_cylinders_beams': '2 / 2',
          'right_time': '09:10',
          'right_atmosphere': '56',
          'right_concrete': '68',
          'right_air_content': '5.5',
          'right_slump': '3.5',
          'right_cylinders_beams': '2 / 2',
        },
      ],
      'qa_rows': [
        {
          'lot_number': '1',
          'lot_size': '400',
          'sublot_number': 'A',
          'sublot_size': '100',
          'random_number': '14',
          'qa_cylinder': 'QA-1',
          'qa_id': 'CYL-1',
          'discrepancy': 'None',
          'discrepancy_cylinder': 'CYL-1',
        },
      ],
      'comments': 'All placement conditions acceptable.',
      'comments_continued': 'Monitor curing through the evening shift.',
      'quantity_rows': [
        {
          'item_or_code_number': '704',
          'sta_to_sta': '10+00 to 12+00',
          'grade_of_concrete': 'Grade P1',
          'length': '200',
          'width': '24',
          'depth': '0.75',
          'measured_sq_or_cu_yards': '133.3',
          'cyds_plan': '135',
          'cyds_used': '136',
          'cyds_waste': '1',
          'over_under_percent': '0.7',
        },
      ],
      'remarks_page1_lines': ['Checked dowel alignment', '', ''],
      'remarks_page2_lines': [
        'Continued observations on page 2',
        '',
        '',
        '',
        '',
        '',
      ],
      'mix_or_street_technician': 'Tech One',
      'mix_or_street_date': '2026-04-09',
      'prepared_by': 'Inspector A',
      'checked_by': 'Engineer B',
      'closeout_date': '2026-04-10',
    }),
  );
}

FormResponse _build1126Response() {
  return FormResponse(
    id: 'resp-1126-pdf-fidelity',
    projectId: 'proj-1126',
    formType: kFormTypeMdot1126,
    headerData: jsonEncode({
      'control_section_id': 'CS-1126',
      'project_number': 'PN-1126',
      'route': 'US-127',
      'construction_engineer': 'Engineer 1126',
      'permit_number': 'PERMIT-9',
      'comprehensive_training_no': 'TRAIN-19',
      'inspector': 'Inspector Name',
      'contractor': 'Prime Contractor',
    }),
    responseData: jsonEncode({
      'header': {
        'project_name': 'PN-1126',
        'contractor_name': 'Prime Contractor',
        'inspector_name': 'Inspector Name',
        'permit_number': 'PERMIT-9',
        'route': 'US-127',
      },
      'report_number': 'R-17',
      'inspection_date': '2026-04-07',
      'date_of_last_inspection': '2026-04-01',
      'remarks': 'Weekly SESC verification artifact.',
      'rainfall_events': [
        {'date': '2026-04-06', 'inches': '0.75'},
        {'date': '2026-04-07', 'inches': '0.10'},
      ],
      'measures': [
        {
          'description': 'Silt fence',
          'location': 'North slope',
          'status': 'in_place',
          'corrective_action': '',
        },
        {
          'description': 'Sediment trap',
          'location': 'Outfall',
          'status': 'needs_action',
          'corrective_action': 'Remove accumulated sediment',
        },
        {
          'description': 'Construction exit',
          'location': 'Gate A',
          'status': 'removed',
          'corrective_action': '',
        },
      ],
    }),
  );
}

IdrPdfData _buildIdrData() {
  final primeContractor = Contractor(
    id: 'prime-1',
    projectId: 'project-1',
    name: 'Prime Builders',
    type: ContractorType.prime,
  );
  final pavingSub = Contractor(
    id: 'sub-1',
    projectId: 'project-1',
    name: 'Paving Sub',
    type: ContractorType.sub,
  );
  final trafficSub = Contractor(
    id: 'sub-2',
    projectId: 'project-1',
    name: 'Traffic Sub',
    type: ContractorType.sub,
  );

  return IdrPdfData(
    entry: DailyEntry(
      id: 'entry-1',
      projectId: 'project-1',
      date: DateTime(2026, 4, 7),
      weather: WeatherCondition.sunny,
      tempLow: 42,
      tempHigh: 68,
      activities:
          'Installed 150 FT of 12" water main and adjusted traffic control.',
      siteSafety: 'Crew used PPE and trench boxes at all open excavations.',
      sescMeasures: 'Silt fence repaired near the north ditch line.',
      trafficControl: 'Lane shift maintained with drums and flaggers.',
      visitors: 'City inspector visited site',
      extrasOverruns:
          'Awaiting force-account approval for additional aggregate.',
      signature: 'Signed by inspector',
      status: EntryStatus.submitted,
    ),
    project: Project(
      id: 'project-1',
      name: 'I-96 Reconstruction',
      projectNumber: 'PN-200',
      clientName: 'MDOT',
    ),
    primeContractor: primeContractor,
    subcontractors: [pavingSub, trafficSub],
    personnelByContractorId: {
      'prime-1': EntryPersonnel(
        entryId: 'entry-1',
        contractorId: 'prime-1',
        foremanCount: 1,
        operatorCount: 2,
        laborerCount: 3,
      ),
      'sub-1': EntryPersonnel(
        entryId: 'entry-1',
        contractorId: 'sub-1',
        foremanCount: 0,
        operatorCount: 1,
        laborerCount: 0,
      ),
      'sub-2': EntryPersonnel(
        entryId: 'entry-1',
        contractorId: 'sub-2',
        foremanCount: 0,
        operatorCount: 1,
        laborerCount: 1,
      ),
    },
    equipmentByContractorId: {
      'prime-1': [
        Equipment(id: 'eq-1', contractorId: 'prime-1', name: 'Excavator 320'),
        Equipment(
          id: 'eq-2',
          contractorId: 'prime-1',
          name: 'Steel Drum Roller',
        ),
      ],
      'sub-1': [Equipment(id: 'eq-3', contractorId: 'sub-1', name: 'Paver')],
      'sub-2': [
        Equipment(id: 'eq-4', contractorId: 'sub-2', name: 'Arrow Board'),
      ],
    },
    usedEquipmentIdsByContractorId: {
      'prime-1': ['eq-1', 'eq-2'],
      'sub-1': ['eq-3'],
      'sub-2': ['eq-4'],
    },
    quantities: [
      EntryQuantity(entryId: 'entry-1', bidItemId: 'bid-1', quantity: 150),
      EntryQuantity(entryId: 'entry-1', bidItemId: 'bid-2', quantity: 42),
    ],
    bidItemsById: {
      'bid-1': BidItem(
        id: 'bid-1',
        projectId: 'project-1',
        itemNumber: '1000',
        description: '12" Water Main',
        unit: 'FT',
        bidQuantity: 1000,
        unitPrice: 125,
      ),
      'bid-2': BidItem(
        id: 'bid-2',
        projectId: 'project-1',
        itemNumber: '2000',
        description: 'Dense Grade HMA',
        unit: 'TON',
        bidQuantity: 500,
        unitPrice: 110,
      ),
    },
    photos: [
      Photo(
        id: 'photo-1',
        entryId: 'entry-1',
        projectId: 'project-1',
        filename: 'IMG_001.jpg',
        filePath: r'C:\temp\IMG_001.jpg',
        caption: 'North ditch repair',
      ),
    ],
    inspectorName: 'Inspector Jane',
    formAttachments: [
      FormAttachment(
        response: FormResponse(
          id: 'form-response-1',
          formType: kFormTypeMdot1126,
          projectId: 'project-1',
          entryId: 'entry-1',
          status: FormResponseStatus.submitted,
        ),
        form: InspectorForm(
          id: kFormTypeMdot1126,
          name: 'MDOT 1126 Weekly SESC',
          templatePath: kFormTemplateMdot1126,
        ),
      ),
    ],
  );
}
