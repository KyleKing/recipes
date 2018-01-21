import glob
import logging
import re

logger = logging.getLogger(__name__)
lgr_fn = 'recipes.log'
formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)d\t%(message)s')

logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(lgr_fn)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


class website_builder(object):
    """Create a new index.html file based on raw markdown templates"""

    index_html = 'index.html'
    template_top = 'src/html/tmpl_top.html'
    template_bot = 'src/html/tmpl_bot.html'
    src_dir = 'content/'
    src_imgs = 'src/imgs/'

    def __init__(self):
        """Prepare output directory and files"""
        open(self.index_html, 'w').close()
        self.cur_md_title = 'NA'

    def make(self):
        """Read from src directory and generate output for website"""
        top = self.read(self.template_top)
        self.write(top)
        markdown_fns = glob.glob('{}*/*.md'.format(self.src_dir))
        markdown_fns = sorted(markdown_fns, key=lambda s: s.lower())
        # Make the Table of Contents, then insert the recipes
        for make_toc in [True, False]:
            # Initialize the state of the TOC list
            if make_toc:
                self.insert_toc_item('init', '')
            else:
                self.insert_toc_item('end', '')
            # Identify each unique recipe file
            sec_name = False
            for markdown_fn in markdown_fns:
                new_sec_name = re.search(ur'\/([^\/]+)\/[^\/]+\.md', markdown_fn).group(1)
                # If new section, create the recipe section dividers
                if new_sec_name != sec_name:
                    if make_toc:
                        self.insert_toc_item('section', new_sec_name)
                    else:
                        logger.debug('')
                        logger.debug('>> Writing Section: {}'.format(new_sec_name))
                        self.start_section(new_sec_name)
                    sec_name = new_sec_name
                if make_toc:
                    # Write a link to the recipe or the recipe content
                    self.insert_toc_item('recipe', markdown_fn)
                else:
                    # Create the recipe
                    self.parse_md(markdown_fn)
        bot = self.read(self.template_bot)
        self.write(bot)

    def read(self, fn, split=False):
        """Return the contents of a file"""
        with open(fn) as fn_:
            contents = fn_.read()
        if split:
            return contents.split('\n')
        else:
            return contents

    def write(self, content, raw_fn=False):
        """Append to the html file"""
        fn = raw_fn if raw_fn else self.index_html
        with open(fn, 'ab') as fn_:
            fn_.write(content)

    # ---------- Create the Table of Contents ---------

    def insert_toc_item(self, match_list_type, item):
        """Track the status of the last list type written"""
        if match_list_type == 'init':
            self.status = {'init': False, 'section': False, 'recipe': False}
            self.write('<h3 style="padding-top: 50px;" id="toc">Recipes Table of Contents</h3>')
        elif match_list_type == 'section':
            # Close the section section, if a recipe section was written
            if self.status['init']:
                self.write('\n\t</ul></li>')
                self.write('\n</ul>')
            self.write('\n<ul>\n\t<li><a href="#{}">{}</a><ul>'.format(item, item))
            self.status['init'] = True
        elif match_list_type == 'recipe':
            title, title_id = self.parse_title(item)
            self.write('\n\t\t<li><a href="#{}">{}</a></li>'.format(title_id, title))
        elif match_list_type == 'end':
            # Close the list div and reset the tracker
            self.write('\n\t</ul></li>')
            self.write('\n</ul>')
            self.status = {'init': False, 'section': False, 'recipe': False}

    def parse_title(self, fn):
        """Retrieve only the title id from the markdown file"""
        for line in self.read(fn, split=True):
            if re.match(ur'^#', line):
                title, title_id = self.make_title(line)
                break
        else:
            return False, False
        return title, title_id

    # ---------- Insert the recipes ---------

    def start_section(self, sec_name):
        """Start a linkable section header"""
        self.write('\n<h1 id="{sec_name}">{sec_name}</h1>\n'.format(sec_name=sec_name))

    def parse_md(self, fn):
        """Parse each line of the markdown file"""
        self.track_list_stat("init")
        for line in self.read(fn, split=True):
            line = self.check_italics(line)
            if re.match(ur'^#', line):
                self.init_recipe(line, fn)
            elif re.match(ur'^-\s', line):
                self.track_list_stat('ul')
                self.append_ingredient(line.strip('-').strip())
            elif re.match(ur'^\d[\.\)]?\s', line):
                self.track_list_stat('ol')
                parsed = re.search('^\d[\.\)]?\s(.+)', line).group(1).strip()
                self.append_list_item(parsed)
            elif re.match(ur'^end$', line):
                self.track_list_stat('end')
            elif len(line) > 0:
                self.other(line)
        # Add the closing div's
        self.write('\n</div><!-- /columns (list) --></div><!-- /row (recipe) -->\n')

    def make_title(self, line):
        title = re.search(ur'#+([^#|]+)', line).group(1).strip()
        return title, 'recipe-{}'.format(title)

    def init_recipe(self, raw_title, full_fn):
        # Solve for variables in markdown layout
        base_name = re.search(ur'[^\/]+\/([^.\/]+)\.md', full_fn).group(1)
        self.cur_md_title = base_name  # track filename for debugging
        logger.debug('')
        logger.debug('> Recipe: {}'.format(self.cur_md_title))
        title, title_id = self.make_title(raw_title)
        header = raw_title.split("||")
        orig_link = header[1].strip() if len(header) == 2 else False
        # Assemble HTML
        classes = 'class="twelve columns" id="{}"'.format(title_id)
        if orig_link:
            # Optional custom source name (## ... || (Book Title) https://www.link.to.book)
            custom_src_exp = ur'\(([^)]+)\)\s*(http.+)'
            if re.match(custom_src_exp, orig_link):
                match = re.search(custom_src_exp, orig_link)
                html_lnk = '<a href="{}"><i>({})</i></a>'.format(match.group(2), match.group(1))
            else:
                html_lnk = '<a href="{}"><i>(Source)</i></a>'.format(orig_link)
        else:
            html_lnk = ''
        ttle_lnk = '<a href="#{}" class="unstyled"># {}</a>'.format(title_id, title)
        header = '<div class="row br"><h5 {}>{} {}</h5></div>'.format(classes, ttle_lnk, html_lnk)
        for image_name in glob.glob('{}{}.*'.format(self.src_imgs, base_name)):
            break
        else:
            image_name = ''
        img_html = '<div class="row">\n<img {} src="{}", alt="{}"/>'.format(
            'class="five columns"', image_name, base_name)
        text_start = '<div class="seven columns">'
        self.write('\n{}\n{}\n{}'.format(header, img_html, text_start))

    def track_list_stat(self, match_list_type):
        """Track the status of the last list type written"""
        if match_list_type == 'init':
            self.status = {"ol": False, "ul": False}
        elif match_list_type == 'ul':
            if not self.status["ul"]:
                self.write("<ul>")
            self.status = {"ol": False, "ul": True}
        elif match_list_type == 'ol':
            if not self.status["ol"]:
                self.write("<ol>")
            self.status = {"ol": True, "ul": False}
        elif match_list_type == 'end':
            # Close the list div and reset the tracker
            if self.status["ol"]:
                self.write("</ol>")
            elif self.status["ul"]:
                self.write("</ul>")
            self.status = {"ol": False, "ul": False}

    def append_ingredient(self, line):
        if '|' in line:
            # Examples from brick_chicken.md
            # 2 tbsp |fresh sage, finely chopped
            # 2 tbsp |canola oil |(or sunflower oil)
            tag = re.match(ur'([^\(+,:]+)', line.split('|')[1]).group(1).strip().title()
            clean_line = re.sub(ur'\s{2,}', ' ', line.replace('|', ''))  # remove unintended whitespace
            self.write('<li class="{}">{}</li>'.format(tag, clean_line))
        else:
            logger.debug('Error: ({}) no ingredient tag in: {}'.format(self.cur_md_title, line))
            self.write('<li>{}</li>'.format(line))

    def append_list_item(self, line):
        self.write('<li>{}</li>'.format(line))

    def other(self, line):
        """Write single line notes/extra information"""
        # logger.debug('Writing paragraph for: {}'.format(line))
        self.write('<p>{}</p>'.format(line))

    def check_italics(self, raw_line):
        if '**' in raw_line:
            line_sections = raw_line.split('**')
            # count_ln = len(line_sections)
            init = True if raw_line[1:2] == '**' else False
            line = ''
            for ls_, line_sec in enumerate(line_sections):
                if init:
                    html = '<i>' if ls_ % 2 == 1 else '</i>'
                else:
                    html = ''
                    init = True
                line += html + line_sec
            # FIXME:
            # logger.debug('Italics: {} > `{}`\n'.format(line_sections, line))
        else:
            line = raw_line
        return line


if __name__ == '__main__':
    open(lgr_fn, 'w').close()
    website_builder().make()
