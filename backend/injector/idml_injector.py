"""Inject English text into Japanese IDML and rebuild as a new IDML file.

Steps:
  E. Replace Japanese Content elements with matched English text
  F. Style adjustments: 85% font size shrink, cyan color for LOW_CONF
  G. Repackage modified XMLs into a valid IDML ZIP
"""

import os
import re
import zipfile
from copy import deepcopy
from dataclasses import dataclass

from lxml import etree

ACE_RE = re.compile(r'<\?ACE\s+\d+\?>')

# CMYK cyan for LOW_CONF highlighting
CYAN_COLOR_SELF = "Color/C=100 M=0 Y=0 K=0"
CYAN_COLOR_NAME = "LOW_CONF_Cyan"
FONT_SHRINK_RATIO = 0.85


@dataclass
class InjectionMapping:
    """A single mapping entry for injection."""
    ja_node_id: str       # e.g. "u78f07_p3"
    en_text: str          # English replacement text
    low_conf: bool        # Whether to mark as LOW_CONF (cyan)


def _parse_node_id(node_id: str) -> tuple[str, int]:
    """Parse 'u78f07_p3' into ('u78f07', 3)."""
    parts = node_id.rsplit("_p", 1)
    return parts[0], int(parts[1])


def _ensure_cyan_color(graphic_xml: bytes) -> bytes:
    """Add a cyan color swatch to Graphic.xml if it doesn't exist."""
    root = etree.fromstring(graphic_xml)
    ns = root.nsmap.get('idPkg', 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging')

    # Check if cyan color already exists
    for color in root.iter('{*}Color'):
        if color.get('Self') == CYAN_COLOR_SELF:
            return graphic_xml  # Already exists

    # Find where to insert (after existing Color elements)
    last_color = None
    for elem in root.iter('{*}Color'):
        last_color = elem

    if last_color is not None:
        cyan = etree.Element('Color')
        cyan.set('Self', CYAN_COLOR_SELF)
        cyan.set('Model', 'Process')
        cyan.set('Space', 'CMYK')
        cyan.set('ColorValue', '100 0 0 0')
        cyan.set('ConvertToHsb', 'false')
        cyan.set('AlternateSpace', 'NoAlternateColor')
        cyan.set('AlternateColorValue', '')
        cyan.set('Name', CYAN_COLOR_NAME)
        cyan.set('ColorEditable', 'true')
        cyan.set('ColorRemovable', 'true')
        cyan.set('Visible', 'true')
        cyan.set('SwatchCreatorID', '7937')

        parent = last_color.getparent()
        idx = list(parent).index(last_color)
        parent.insert(idx + 1, cyan)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes')


def _inject_story(
    story_xml: bytes,
    mappings_for_story: dict[int, InjectionMapping],
    min_text_length: int = 2,
) -> bytes:
    """Inject English text into a single Story XML.

    Args:
        story_xml: Original Story XML bytes
        mappings_for_story: dict of paragraph_index -> InjectionMapping
        min_text_length: Minimum text length (same as extractor)

    Returns:
        Modified Story XML bytes
    """
    root = etree.fromstring(story_xml)

    # Find the Story element
    story_elem = None
    for child in root:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'Story':
            story_elem = child
            break

    if story_elem is None:
        return story_xml

    # Walk through ParagraphStyleRanges, tracking paragraph index
    # This must match the extraction logic exactly
    para_idx = 0

    for psr in list(story_elem):
        tag = psr.tag.split('}')[-1] if '}' in psr.tag else psr.tag
        if tag != 'ParagraphStyleRange':
            continue

        # Collect paragraph segments: groups of Content elements between Br markers
        # Each group = one paragraph
        current_segment: list[tuple[etree._Element, etree._Element]] = []  # (csr, content)

        for csr in list(psr):
            csr_tag = csr.tag.split('}')[-1] if '}' in csr.tag else csr.tag

            if csr_tag == 'CharacterStyleRange':
                for child in list(csr):
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                    if child_tag == 'Content':
                        text = child.text or ''
                        cleaned = ACE_RE.sub('', text)
                        if cleaned:
                            current_segment.append((csr, child))

                    elif child_tag == 'Br':
                        # Flush paragraph
                        if current_segment:
                            joined = ''.join(
                                ACE_RE.sub('', c.text or '') for _, c in current_segment
                            ).strip()
                            if len(joined) >= min_text_length:
                                _apply_injection(current_segment, para_idx, mappings_for_story)
                                para_idx += 1
                        current_segment = []

            elif csr_tag == 'Table':
                # Handle table cells as individual paragraphs
                for cell in csr.findall('.//{*}Cell'):
                    cell_contents = []
                    for content in cell.findall('.//{*}Content'):
                        t = ACE_RE.sub('', content.text or '')
                        if t:
                            csr_parent = content.getparent()
                            cell_contents.append((csr_parent, content))
                    if cell_contents:
                        cell_text = ''.join(
                            ACE_RE.sub('', c.text or '') for _, c in cell_contents
                        ).strip()
                        if len(cell_text) >= min_text_length:
                            _apply_injection(cell_contents, para_idx, mappings_for_story)
                            para_idx += 1

        # Remaining text after last Br
        if current_segment:
            joined = ''.join(
                ACE_RE.sub('', c.text or '') for _, c in current_segment
            ).strip()
            if len(joined) >= min_text_length:
                _apply_injection(current_segment, para_idx, mappings_for_story)
                para_idx += 1

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes')


def _apply_injection(
    segment: list[tuple[etree._Element, etree._Element]],
    para_idx: int,
    mappings: dict[int, InjectionMapping],
) -> None:
    """Apply text replacement and style changes to a paragraph segment.

    Args:
        segment: list of (CharacterStyleRange, Content) element pairs
        para_idx: Current paragraph index
        mappings: dict of paragraph_index -> InjectionMapping
    """
    if para_idx not in mappings:
        return

    mapping = mappings[para_idx]

    # Put English text in the first Content element, clear the rest
    for i, (csr, content) in enumerate(segment):
        if i == 0:
            content.text = mapping.en_text
            point_size = csr.get("PointSize")
            if point_size:
                try:
                    new_size = float(point_size) * FONT_SHRINK_RATIO
                    csr.set("PointSize", f"{new_size: .2f}")
                except ValueError:
                    pass

            if mapping.low_conf:
                csr.set('FillColor', CYAN_COLOR_SELF)
        else:
            content.text = ""


def build_english_idml(
    source_idml_path: str,
    output_idml_path: str,
    mappings: list[dict],
) -> str:
    """Build an English IDML file by injecting mapped text.

    Args:
        source_idml_path: Path to the original Japanese IDML
        output_idml_path: Path for the output English IDML
        mappings: List of mapping dicts with ja_node_id, en_text, low_conf, score

    Returns:
        Path to the generated IDML file
    """
    # Group mappings by story_id
    story_mappings: dict[str, dict[int, InjectionMapping]] = {}
    for m in mappings:
        story_id, para_idx = _parse_node_id(m['ja_node_id'])
        if story_id not in story_mappings:
            story_mappings[story_id] = {}
        story_mappings[story_id][para_idx] = InjectionMapping(
            ja_node_id=m['ja_node_id'],
            en_text=m['en_text'],
            low_conf=m.get('low_conf', False),
        )

    os.makedirs(os.path.dirname(output_idml_path) or '.', exist_ok=True)

    with zipfile.ZipFile(source_idml_path, 'r') as zin:
        with zipfile.ZipFile(output_idml_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item)

                # Inject English text into relevant Story files
                if item.startswith('Stories/Story_'):
                    story_id = item.split('/')[-1].replace('Story_', '').replace('.xml', '')
                    if story_id in story_mappings:
                        data = _inject_story(data, story_mappings[story_id])

                # Add cyan color to Graphic.xml
                elif item == 'Resources/Graphic.xml':
                    # Only add cyan color if we have LOW_CONF mappings
                    has_low_conf = any(
                        m.low_conf
                        for sm in story_mappings.values()
                        for m in sm.values()
                    )
                    if has_low_conf:
                        data = _ensure_cyan_color(data)

                zout.writestr(item, data)

    return output_idml_path

