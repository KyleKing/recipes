# Notes

## Archived Code

Recursive programming snippet for generating markdown lists from dictionaries or lists

```py
def format_md_list(iterator: Union[dict, Iterable], list_prefix: str = '*') -> List[str]:
    """Recursively format a markdown list interpreting a dictionary as a multi-level list."""
    out = []
    logger.debug('({type_iter}) iterator={iterator}', iterator=iterator, type_iter=type(iterator))
    if isinstance(iterator, dict):
        for key, values in iterator.items():
            logger.debug('{key}: ({type_values}) {values}', key=key, values=values, type_values=type(values))
            out.append(f'{list_prefix} {key}')
            out.extend(format_md_list(values, '    ' + list_prefix))
    else:
        out.extend([f'{list_prefix} {value}' for value in iterator])
    logger.debug('Created: {out}', out=out)
    return out


def format_md_task_list(iterator: Union[dict, Iterable]) -> List[str]:
    """Run format_md_list with the default list prefix set to a check or task list format."""
    logger.debug('Starting "format_md_task_list": {iterator}', iterator=iterator)
    return format_md_list(iterator, list_prefix='* [ ]')
```
