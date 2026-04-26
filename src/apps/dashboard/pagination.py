from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def paginate_queryset(request, queryset, page_size=None):
    """
    Paginate a queryset based on request parameters.
    
    Args:
        request: Django HTTP request
        queryset: QuerySet to paginate
        page_size: Optional page size override
    
    Returns:
        tuple: (paginated_object, page_obj)
    """
    if page_size is None:
        page_size = request.GET.get('page_size', DEFAULT_PAGE_SIZE)
    
    try:
        page_size = int(page_size)
        page_size = min(page_size, MAX_PAGE_SIZE)  # Cap at max
    except (ValueError, TypeError):
        page_size = DEFAULT_PAGE_SIZE
    
    paginator = Paginator(queryset, page_size)
    
    page = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return paginator, page_obj


def get_pagination_context(paginator, page_obj, page_size=None):
    """
    Get common context variables for pagination templates.
    """
    return {
        'paginator': paginator,
        'page_obj': page_obj,
        'page_size': page_size or DEFAULT_PAGE_SIZE,
        'page_sizes': [10, 25, 50, 100],
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }
