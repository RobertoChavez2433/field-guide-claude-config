import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:syncfusion_flutter_pdf/pdf.dart';

void main() {
  test('verifies saved local all-cell PDF artifacts', () {
    const root =
        '.codex/artifacts/2026-04-11/final_form_fillout/local_all_cell';
    final proofLines = <String>[];

    _verifyExport('$root/generated_0582b_full_capacity.pdf', {
      'DATE': '2026-04-07',
      '1Row1': '1',
      '1Row12': '12',
      '7Row12': '142.2',
      'FRow5': isNotEmpty,
      'DENSITYRow2': '475.0',
      'REMARKS 1': '0582B all mapped rows populated.',
    }, proofLines);
    _verifyPreview(
      '$root/preview_0582b_full_capacity_read_only.pdf',
      proofLines,
    );

    _verifyExport('$root/generated_1126_full_capacity.pdf', {
      'CONTROL SECTION': 'CS-1126',
      'REPORT NUMBER': '1126-ALL',
      'TYPE OF CONTROLRow1': 'Control 1',
      'TYPE OF CONTROLRow7': 'Control 7',
      'REMARKSRow1': 'All mapped SESC cells populated for verification.',
    }, proofLines);
    _verifyPreview(
      '$root/preview_1126_full_capacity_read_only.pdf',
      proofLines,
    );

    _verifyExport('$root/generated_1174r_full_capacity.pdf', {
      'Text4': '1174-ALL',
      'Text14.0': '08:00',
      'Text14.1.1.1.1': '08:40',
      'Text26.6': 'Lot-6',
      'Text37.5': '705',
      'Text55': '2026-04-10',
    }, proofLines);
    _verifyPreview(
      '$root/preview_1174r_full_capacity_read_only.pdf',
      proofLines,
    );

    _verifyExport('$root/generated_idr_full_capacity.pdf', {
      'Text10': '4/8/26',
      'Namegdzf': 'Prime Builders',
      'hhhhhhhhhhhwerwer': 'Prime Builders Eq 14',
      'Text6': contains('MDOT 0582B Density Report (Submitted)'),
    }, proofLines);
    _verifyPreview('$root/preview_idr_full_capacity_read_only.pdf', proofLines);

    File('$root/syncfusion_parsed_field_proof.txt')
      ..createSync(recursive: true)
      ..writeAsStringSync(proofLines.join('\n'));
  });
}

void _verifyExport(
  String path,
  Map<String, Object> expectations,
  List<String> proofLines,
) {
  final document = PdfDocument(inputBytes: File(path).readAsBytesSync());
  try {
    expect(document.form.fields.count, greaterThan(0), reason: path);
    proofLines.add('');
    proofLines.add(path);
    proofLines.add('field_count=${document.form.fields.count}');
    for (final entry in expectations.entries) {
      final value = _textValue(document.form, entry.key);
      expect(value, entry.value, reason: '$path ${entry.key}');
      proofLines.add('${entry.key}=$value');
    }
  } finally {
    document.dispose();
  }
}

void _verifyPreview(String path, List<String> proofLines) {
  final document = PdfDocument(inputBytes: File(path).readAsBytesSync());
  try {
    expect(document.form.fields.count, 0, reason: path);
    proofLines.add('');
    proofLines.add(path);
    proofLines.add('field_count=0');
  } finally {
    document.dispose();
  }
}

String _textValue(PdfForm form, String fieldName) {
  for (var i = 0; i < form.fields.count; i++) {
    final field = form.fields[i];
    if (field.name == fieldName) {
      if (field is PdfTextBoxField) return field.text;
      if (field is PdfComboBoxField) return field.selectedValue;
      fail('Expected "$fieldName" to be text-like, got ${field.runtimeType}');
    }
  }
  fail('Field "$fieldName" not found');
}
