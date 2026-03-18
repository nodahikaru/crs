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


def _content_segments(content_elem) -> list[str]:
    """Split a <Content> element on embedded <?ACE N?> processing instructions.

    Returns one cleaned string per segment delimited by ACE PIs.
    """
    segments: list[str] = []

    first = (content_elem.text or '').strip()
    if first:
        segments.append(first)

    for child in content_elem:
        tail = (child.tail or '').strip()
        if tail:
            segments.append(tail)

    return segments


class _PITailProxy:
    """Write-target proxy for a ProcessingInstruction's tail text.

    Allows _apply_injection to write back to a PI tail using the same
    ``obj.text = value`` interface it uses for Content elements.
    """
    __slots__ = ('_pi',)

    def __init__(self, pi_elem) -> None:
        self._pi = pi_elem

    @property
    def text(self) -> str:
        return self._pi.tail or ''

    @text.setter
    def text(self, value: str) -> None:
        self._pi.tail = value


def _iter_content_write_targets(csr, content_elem):
    """Yield (csr, write_target) pairs for each ACE-delimited text segment.

    The first segment uses the Content element itself (writes to .text).
    Subsequent segments use _PITailProxy wrappers (writes to PI .tail).
    Only yields pairs where the segment has non-empty text.
    """
    first = (content_elem.text or '').strip()
    if first:
        yield csr, content_elem

    for child in content_elem:
        tail = (child.tail or '').strip()
        if tail:
            yield csr, _PITailProxy(child)

# Matches text that contains at least one letter (Latin or CJK/kana)
_HAS_LETTER_RE = re.compile(r'[A-Za-z\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]')


def _is_numeric_symbol_only(text: str) -> bool:
    """Return True if text contains no letters — only digits, %, punctuation, etc."""
    return not bool(_HAS_LETTER_RE.search(text))

# CMYK cyan for LOW_CONF highlighting
CYAN_COLOR_SELF = "Color/C=100 M=0 Y=0 K=0"
CYAN_COLOR_NAME = "LOW_CONF_Cyan"
HIGHLIGHT_SHADING_TYPE = "Solid"
FONT_SHRINK_RATIO = 0.85


@dataclass
class InjectionMapping:
    """A single mapping entry for injection."""
    ja_node_id: str       # e.g. "u78f07_p3"
    en_text: str          # English replacement text
    low_conf: bool        # Whether to mark as LOW_CONF (cyan)


def _parse_node_id(node_id: str) -> tuple[str, int, int | None]:
    """Parse 'u78f07_p3_s2' into ('u78f07', 3, 2) or ('u78f07', 3, None)."""
    story_part, rest = node_id.split("_p", 1)
    if "_s" in rest:
        para_str, sent_str = rest.split("_s", 1)
        return story_part, int(para_str), int(sent_str)
    return story_part, int(rest), None


def _ensure_cyan_color(graphic_xml: bytes) -> bytes:
    """Add a cyan color swatch to Graphic.xml if it doesn't exist."""
    root = etree.fromstring(graphic_xml)
    ns = root.nsmap.get('idPkg', 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging')

    # Check if cyan color already exists
    for color in root.iter('{*}Color'):
        if color.get('Self') == CYAN_COLOR_SELF or color.get('Name') == CYAN_COLOR_NAME:
            return graphic_xml  # Already exists

    # Find where to insert (after existing Color elements)
    last_color = None
    for elem in root.iter('{*}Color'):
        last_color = elem

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

    if last_color is not None:
        parent = last_color.getparent()
        idx = list(parent).index(last_color)
        parent.insert(idx + 1, cyan)
    else:
        root.append(cyan)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes')


def split_japanese_sentences(text: str) -> list[str]:
    if not text:
        return []

    parts = re.split(r'(?<=[。？！]|\.|\?|!)\s*', text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def _inject_story(
    story_xml: bytes,
    mappings_for_story: dict[tuple[int, int], InjectionMapping],
    min_text_length: int = 2,
) -> bytes:
    """Inject English text into a single Story XML.

    Args:
        story_xml: Original Story XML bytes
        mappings_for_story: dict of (paragraph_index, sentence_index) -> InjectionMapping
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

    para_idx = 0

    def _flush_current_segment():
        nonlocal para_idx, current_segment
        if not current_segment:
            return

        joined = ''.join(
            ACE_RE.sub('', c.text or '') for _, c in current_segment
        ).strip()
        if len(joined) >= min_text_length:
            paragraph_mappings = {
                sidx: m
                for (pidx, sidx), m in mappings_for_story.items()
                if pidx == para_idx
            }
            sentences = split_japanese_sentences(joined)
            replaced = []
            low_conf = False
            for sidx, sent in enumerate(sentences):
                mapping = paragraph_mappings.get(sidx)
                if mapping:
                    replaced.append(mapping.en_text)
                    low_conf = low_conf or mapping.low_conf
                else:
                    replaced.append(sent)

            merged_text = ''.join(replaced)
            if merged_text != joined or paragraph_mappings:
                temp_mapping = {
                    para_idx: InjectionMapping(
                        ja_node_id=f"{para_idx}",
                        en_text=merged_text,
                        low_conf=low_conf,
                    )
                }
                _apply_injection(current_segment, para_idx, temp_mapping)
        para_idx += 1
        current_segment = []

    for psr in list(story_elem):
        tag = psr.tag.split('}')[-1] if '}' in psr.tag else psr.tag
        if tag != 'ParagraphStyleRange':
            continue

        current_segment: list[tuple[etree._Element, etree._Element]] = []

        for csr in list(psr):
            csr_tag = csr.tag.split('}')[-1] if '}' in csr.tag else csr.tag
            if csr_tag == 'CharacterStyleRange':
                for child in list(csr):
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                    if child_tag == 'Content':
                        # Iterate ACE-delimited segments; flush at each boundary
                        # so every segment becomes its own logical paragraph,
                        # matching the extractor's node splitting.
                        write_targets = list(_iter_content_write_targets(csr, child))
                        if not write_targets:
                            pass
                        elif len(write_targets) == 1:
                            current_segment.append(write_targets[0])
                        else:
                            # First segment joins current paragraph
                            current_segment.append(write_targets[0])
                            # Each subsequent segment is a new paragraph
                            for wt in write_targets[1:]:
                                _flush_current_segment()
                                current_segment.append(wt)

                    elif child_tag == 'Br':
                        _flush_current_segment()

                    elif child_tag == 'Table':
                        # Flush any pending segment before processing table cells
                        _flush_current_segment()

                        for cell in child.findall('.//Cell'):
                            cell_contents = []
                            for content in cell.findall('.//Content'):
                                t = ACE_RE.sub('', content.text or '')
                                if t:
                                    csr_parent = content.getparent()
                                    cell_contents.append((csr_parent, content))
                            if cell_contents:
                                cell_text = ''.join(
                                    ACE_RE.sub('', c.text or '') for _, c in cell_contents
                                ).strip()
                                if len(cell_text) >= min_text_length and not _is_numeric_symbol_only(cell_text):
                                    paragraph_mappings = {
                                        sidx: m
                                        for (pidx, sidx), m in mappings_for_story.items()
                                        if pidx == para_idx
                                    }
                                    sentences = split_japanese_sentences(cell_text)
                                    replaced = []
                                    low_conf = False
                                    for sidx, sent in enumerate(sentences):
                                        mapping = paragraph_mappings.get(sidx)
                                        if mapping:
                                            replaced.append(mapping.en_text)
                                            low_conf = low_conf or mapping.low_conf
                                        else:
                                            replaced.append(sent)

                                    merged_text = ''.join(replaced)
                                    temp_mapping = {
                                        para_idx: InjectionMapping(
                                            ja_node_id=f"{para_idx}",
                                            en_text=merged_text,
                                            low_conf=low_conf,
                                        )
                                    }
                                    _apply_injection(cell_contents, para_idx, temp_mapping)
                                    para_idx += 1

        if current_segment:
            joined = ''.join(
                ACE_RE.sub('', c.text or '') for _, c in current_segment
            ).strip()
            if len(joined) >= min_text_length:
                paragraph_mappings = {
                    sidx: m
                    for (pidx, sidx), m in mappings_for_story.items()
                    if pidx == para_idx
                }
                sentences = split_japanese_sentences(joined)
                replaced = []
                low_conf = False
                for sidx, sent in enumerate(sentences):
                    mapping = paragraph_mappings.get(sidx)
                    if mapping:
                        replaced.append(mapping.en_text)
                        low_conf = low_conf or mapping.low_conf
                    else:
                        replaced.append(sent)

                merged_text = ''.join(replaced)
                if merged_text != joined or paragraph_mappings:
                    temp_mapping = {
                        para_idx: InjectionMapping(
                            ja_node_id=f"{para_idx}",
                            en_text=merged_text,
                            low_conf=low_conf,
                        )
                    }
                    _apply_injection(current_segment, para_idx, temp_mapping)
                para_idx += 1

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes')


def _apply_injection(
    segment: list[tuple[etree._Element, etree._Element]],
    para_idx: int,
    mappings: dict[int, InjectionMapping],
) -> None:
    if para_idx not in mappings:
        return

    mapping = mappings[para_idx]

    for i, (csr, content) in enumerate(segment):
        if i == 0:
            content.text = mapping.en_text

            # ✅ Apply styling ONLY to injected content
            if mapping.low_conf:
                csr.set('Underline', 'true')
                csr.set('UnderlineColor', CYAN_COLOR_SELF)
                csr.set('UnderlineTint', '40')
                csr.set('UnderlineWeight', '10')
                csr.set('UnderlineOffset', '-2')
                csr.set('UnderlineType', 'StrokeStyle/$ID/Solid')

        else:
            content.text = ''

        # shrink still applies to all (this is fine)
        point_size = csr.get('PointSize')
        if point_size:
            try:
                new_size = float(point_size) * FONT_SHRINK_RATIO
                csr.set('PointSize', f"{new_size:.2f}")
            except ValueError:
                pass

        # All English replacements: reduce leading by 2pt
        # Auto leading = PointSize * 1.2 (InDesign default)
        leading = csr.get('Leading')
        if leading == 'Auto' or not leading:
            point_size = csr.get('PointSize')
            if point_size:
                try:
                    auto_leading = float(point_size) * 1.2
                    csr.set('Leading', f"{auto_leading - 2:.2f}")
                except ValueError:
                    pass
        else:
            try:
                csr.set('Leading', f"{float(leading) - 2:.2f}")
            except ValueError:
                pass


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
    # Group mappings by story_id and (paragraph, sentence)
    story_mappings: dict[str, dict[tuple[int, int], InjectionMapping]] = {}
    for m in mappings:
        story_id, para_idx, sent_idx = _parse_node_id(m['ja_node_id'])
        if sent_idx is None:
            continue
        if story_id not in story_mappings:
            story_mappings[story_id] = {}
        story_mappings[story_id][(para_idx, sent_idx)] = InjectionMapping(
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