from django.shortcuts import render, redirect, get_object_or_404, redirect
from django.http import HttpResponse, Http404

from django.views import generic
from .models import *
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .forms import *

from django.contrib import messages

# from django.contrib.auth.models import User
# from django.contrib.auth import get_user_model
from accounts.models import User

from django.utils import timezone
import os

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from django_datatables_view.base_datatable_view import BaseDatatableView
# from ajax_datatable.views import AjaxDatatableView

from django.conf import settings
from django.http import JsonResponse

import operator

#HTML除去
from django.utils.html import strip_tags

import requests

#個別ブラウザ通知の関数
def onegisnal_id_create(request):
    onesignal_user_id = request.POST['id']
    OneSignalUser.objects.create(onesignal_user_id=onesignal_user_id)
    return HttpResponse('ok')


#Ajaxで未読削除
def ajax_read_delete(request, pk, *args, **kwargs):
    if request.is_ajax():
        ReadStates.objects.filter(user=request.user, information=pk).delete()
        return JsonResponse({"message":"success"})


#関数ビューで通知の中間テーブルCreateを作ってみる
def add_fbvform(request):
    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES)

        if form.is_valid(): 
            obj = form.save(commit=False)
            obj.user = request.user
            obj.created_at = timezone.datetime.now()
            obj.updated_at = timezone.datetime.now()

            #下書きチェックだったら
            if request.POST.get('draft') is not None: 
                obj.is_draft = True

            #html除去
            obj.non_html = strip_tags(request.POST.get('body'))

            obj.save()

            #添付ファイル：保存＆モデル書き込み
            # pdf_files = request.FILES.getlist()
            # for pdf in pdf_files:
            if 'pdf_file1' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file1'] , information=obj)
                instance.save()

            if 'pdf_file2' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file2'] , information=obj)
                instance.save()

            if 'pdf_file3' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file3'] , information=obj)
                instance.save()

            # user = get_object_or_404(User, pk=request.POST["notification_user"])#これで出来た

            #通知：選択したユーザー
            result = request.POST.getlist("tags")
            for user in result:
                user_instance = get_object_or_404(User, pk=user)
                # Notifications.objects.create(user=user_instance, information=obj)
                #既読も同じでok？
                ReadStates.objects.create(user=user_instance, information=obj)


             #ブラウザ通知：できたらmodel.pyにクラス書く→できたら、model.pyクラス外に関数化して書く
            if request.POST.get('draft') is None: 
                #ブラウザ通知：直書き
                # data = {
                #     'app_id': '6027ee57-82ec-485b-a5a5-6c976de75cb1',
                #     'included_segments': ['All'],
                #     'contents': {'en': 'info create'},
                #     'headings': {'en': 'お知らせが作成されました'},
                #     'url': resolve_url('myinfo:index'),
                # }
                # requests.post(
                #     "https://onesignal.com/api/v1/notifications",
                #     headers={'Authorization': 'Basic NDQ4Y2RiZTctNTgxMy00ZTc2LWFiYzctZTRiZGMyMGYwNjJh'},  # 先頭にBasic という文字列がつく
                #     json=data,
                # )

                #汎用のブラウザ通知関数呼び出し
                # title = request.POST.get('title')
                # browser_push(
                #     title,
                #     'お知らせが作成されました',
                #     resolve_url('myinfo:index')
                # )

                #モデルインスタンスのブラウザ通知メソッド呼び出し
                obj.browser_push(request)

            return redirect('myinfo:index')

    else:
        form = InformationForm

        #ここに

    return render(request, 'myinfo/add_fbvform.html', {'form': form })


#Detail関数ビュー
def detail_fbvform(request, pk):
    template_name = "myinfo/information_detail.html"

    try:
        information = Information.objects.get(pk=pk)
    except Information.DoesNotExist:
        raise Http404("Information does not exist")

    #コメント入力時
    if request.method == 'POST':

        # 投稿されたコメントをデータベースに保存
        if request.POST["text"] != "":
            InfoComments.objects.create(
                comment=request.POST["text"],
                information=information,
                user = request.user
                )
        else:
            messages.warning(request, 'コメント欄は未入力です')
    
    #通知表示用（有無だけ）
    if request.user.id is not None:
        notifi_exis =  Notifications.objects.filter(user=request.user).exists()

        context = {
            "information":information,
            'notifi_exis':notifi_exis,
        }

        #既読にする（中間テーブルから削除する）
        read_exis = ReadStates.objects.filter(user=request.user, information=pk).exists()
        if read_exis == True:
            ReadStates.objects.filter(user=request.user, information=pk).delete()

    else:
        context = {
            "information":information,
        }

    return render(request,template_name,context)


#Update関数ビューつくる
def edit_fbvform(request, pk, *args, **kwargs):

    information = get_object_or_404(Information, pk=pk)

    #外部キーなので_set.all()でなくrelated_nameで
    attachments = information.info_attach.all()
    notifications = information.info_notifi.all()
    read_states = information.info_read.all()
    
    if request.method == 'POST':
        form = InformationEditForm(request.POST, request.FILES, instance=information)

        if form.is_valid(): 
            obj = form.save(commit=False)
            obj.user = request.user

            #更新日時も更新するチェックだったら
            if request.POST.get('chk') is not None: 
                obj.updated_at = timezone.datetime.now()

            #下書きチェックだったら
            if request.POST.get('draft') is not None: 
                obj.is_draft = True
            else:
                obj.is_draft = False

            #html除去
            obj.non_html = strip_tags(request.POST.get('body'))

            obj.save()

            #添付ファイル3つ
            if 'pdf_file1' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file1'] , information=obj)
                instance.save()
            if 'pdf_file2' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file2'] , information=obj)
                instance.save()
            if 'pdf_file3' in request.FILES:
                instance = Attachments(file_path=request.FILES['pdf_file3'] , information=obj)
                instance.save()

            #全員未読にするチェックだったら
            if request.POST.get('chk2') is not None: 
                #通知：選択したユーザー
                result = request.POST.getlist("tags")
                for user in result:
                    # user_instance = User.objects.get(pk=user)#これ出来ない・
                    user_instance = get_object_or_404(User, pk=user)
                    # Notifications.objects.get_or_create(user=user_instance, information=obj)
                    #既読も
                    ReadStates.objects.get_or_create(user=user_instance, information=obj)


            request.session['form_data'] = request.POST

            if request.POST.get('draft') is None:
                #モデルインスタンスのブラウザ通知メソッド呼び出し
                obj.browser_push(request)

            messages.success(request, '更新しました！')
            return redirect('myinfo:detail', pk=pk)

        else:
            messages.error(request, '更新できませんでした。内容を確認してください。')
            return redirect('myinfo:update', pk=pk)


    # 一覧表示からの遷移や、確認画面から戻った時
    form = InformationEditForm(instance=information)

    context ={
        'form': form,
        'information':information,
        'notification':notifications,
        'attachment':attachments,
        'read_state':read_states,
        
    }

    return render(request, 'myinfo/edit_fbvform.html', context)


#使用中のidndex
def information_list(request):

    #検索
    #検索結果をページネーションするにはSessionから条件取得？
    #→中止して、検索の場合、ページネーションなしにしよう。  
    searchForm = SearchForm(request.GET)

    context = {
        'searchForm': searchForm,
    }

    if searchForm.is_valid():
        # informations = Information.objects.filter(title__contains=keyword).order_by('-id')#ひとまずタイトルに含む
        # タイトルor本文に含む（複数ワード、区切りは半角でも全角スペースでもOK
        queryset = Information.objects.all()
        keyword = searchForm.cleaned_data['keyword']
        if keyword:
            keyword = keyword.split()
            for k in keyword:
                queryset = queryset.filter(
                        Q(title__icontains=k) | 
                        # Q(body__icontains=k)
                        Q(non_html__icontains=k) | 
                        Q(for_search__icontains=k)
                    ).order_by('-updated_at')#

            context['informations'] = queryset
    else:
        searchForm = SearchForm()
        informations = Information.objects.all().order_by('-updated_at')
        page_obj = paginate_queryset(request, informations, 10)#ページネーション用
        context['page_obj'] = page_obj
        context['informations'] = page_obj.object_list

    #通知（有無だけ）
    if request.user.id is not None:
        notifi_exis =  Notifications.objects.filter(user=request.user).exists()

        #既読も
        # my_unread = ReadStates.objects.all().filter(user=request.user)
        unread_set = ReadStates.objects.all()

        #contextは辞書型、context['weather'] = '晴れ'、でkeyがweather、valueが晴れというデータを追加
        context['notifi_exis'] = notifi_exis
        context['unread_set'] = unread_set


    return render(request, 'myinfo/information_list.html', context)


#ページネーション
def paginate_queryset(request, queryset, count):
    paginator = Paginator(queryset, count)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return page_obj


class DeleteView(LoginRequiredMixin, generic.edit.DeleteView):
    model = Information
    success_url = reverse_lazy('myinfo:index')

    def delete(self, request, *args, **kwargs):
        self.object = post = self.get_object()
        message = f'削除しました！'
        post.delete()
        messages.info(self.request, message)
        return redirect(self.get_success_url())


UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__)) + '/uploads/'  # アップロードしたファイルを保存するディレクトリ
#同じファイル名は上書き保存されてしまうけど
def handle_uploaded_file(f):
    path = os.path.join(UPLOAD_DIR, f.name)#これ追記：これで引っ張ってくる
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

#通知削除
def notifi_delete(request):
    Notifications.objects.filter(user=request.user).delete()

    # return redirect('myinfo:index')
    return redirect(request.META['HTTP_REFERER'])#元のページに戻る

#添付削除
def attach_delete(request, pk):
    Attachments.objects.filter(pk=pk).delete()
    return redirect(request.META['HTTP_REFERER'])#元のページに戻る

#listからの既読削除
def read_delete(request, pk):
    #既読にする（中間テーブルから削除する）
    read_exis = ReadStates.objects.filter(user=request.user, information=pk).exists()
    if read_exis == True:
        ReadStates.objects.filter(user=request.user, information=pk).delete()
    return redirect(request.META['HTTP_REFERER'])#元のページに戻る


#シフト表
def shift(request):

    workshifts = WorkShifts.objects.all().order_by('-created_at')
    context = {
        "workshifts":workshifts,
    }

    return render(request, 'myinfo/shift.html', context)


#FAQリスト
def faqs_list(request):

    faqsearchForm = FaqSearchForm(request.GET)

    context = {
        'faqsearchForm': faqsearchForm,
    }
    #ディーラーのall←全部とってくる用
    #窓口のallは使わないか
    #別フィールド作ってTrueFalseで分岐をテンプレートに書く（or紐付いていなかったらallということにするか）
    context['dealers_all'] = Dealers.objects.all().order_by('id')
    context['contacts_all'] = Contacts.objects.all().order_by('id')
    #↓1件でもクエリセットだとtemplateでループ要になるため、firstつける
    context['helpdesk'] = Contacts.objects.filter(name__contains="日産ヘルプデスク").first()

    #振り先一覧pdfのパス
    context['furisaki'] = Attachments.objects.filter(file_path__contains="振り先一覧").first()

    if faqsearchForm.is_valid():
        queryset = Faqs.objects.all()
        keyword = faqsearchForm.cleaned_data['keyword']
        if keyword:
            keyword = keyword.split()
            for k in keyword:
                queryset = queryset.filter(
                        # Q(question__icontains=k) | 
                        # Q(answer1__icontains=k) | 
                        # Q(answer2__icontains=k) | 
                        # Q(reference__icontains=k)
                        Q(non_html__icontains=k)
                    ).order_by('-updated_at')#

            context['faqs'] = queryset
            context['selected_tab'] = '検索結果'
    else:
        faqsearchForm = FaqSearchForm()
        faqs = Faqs.objects.all().order_by('-updated_at', 'id')
        page_obj = paginate_queryset(request, faqs, 50)#ページネーション用
        context['page_obj'] = page_obj
        context['faqs'] = page_obj.object_list
        context['selected_tab'] = 'すべて'


    return render(request, 'myinfo/faqs.html', context)


#FAQタブ、共通化で作れるか
def faqs_tab(request, p):

    faqsearchForm = FaqSearchForm(request.GET)

    context = {
        'faqsearchForm': faqsearchForm,
    }

    context['dealers_all'] = Dealers.objects.all().order_by('id')
    context['contacts_all'] = Contacts.objects.all().order_by('id')
    #↓1件でもクエリセットだとtemplateでループ要になるため、firstつける
    context['helpdesk'] = Contacts.objects.filter(name__contains="日産ヘルプデスク").first()

    #振り先一覧pdfのパス
    context['furisaki'] = Attachments.objects.filter(file_path__contains="振り先一覧").first()

    # 一度queryset = Faqs.objects.all()と刻む必要はない
    queryset = Faqs.objects.filter(
                Q(reference__icontains=p)
            ).order_by('-updated_at')
    context['selected_tab'] = p
    context['faqs'] = queryset

    return render(request, 'myinfo/faqs.html', context)



#FAQ Datatablesバージョン未使用
class FaqsJsonView(BaseDatatableView):
    # モデルの指定
    model = Faqs
    # 表示するフィールドの指定
    columns = ['id', 'question', 'answer1', 'answer2', 'reference']


    def filter_queryset(self, qs):

        search = self.request.GET.get('search[value]', None)
        if search:
            search_parts = search.split()
            for part in search_parts:
                qs = qs.filter(
                        Q(question__icontains=part) | 
                        Q(answer1__icontains=part) | 
                        Q(answer2__icontains=part) | 
                        Q(reference__icontains=part)
                    )
        return qs


#全体検索
def all_search(request):

    keyword = request.GET.get('all_search')
    context = {
        'keyword': keyword,
    }

    context['dealers_all'] = Dealers.objects.all().order_by('id')
    context['contacts_all'] = Contacts.objects.all().order_by('id')
    #↓1件でもクエリセットだとtemplateでループ要になるため、firstつける
    context['helpdesk'] = Contacts.objects.filter(name__contains="日産ヘルプデスク").first()

    #おしらせの検索ここに
    queryset = Information.objects.all()
    if keyword:
        keyword = keyword.split()
        for k in keyword:
            queryset = queryset.filter(
                    Q(title__icontains=k) | 
                    # Q(body__icontains=k)
                    Q(non_html__icontains=k) | 
                    Q(for_search__icontains=k)
                ).order_by('-updated_at')#

        # context = {
        #     'informations': queryset,
        # }
        context['informations'] = queryset


    #FAQ
    queryset = Faqs.objects.all()
    keyword = request.GET.get('all_search')
    if keyword:
        keyword = keyword.split()
        for k in keyword:
            queryset = queryset.filter(
                    # Q(question__icontains=k) | 
                    # Q(answer1__icontains=k) | 
                    # Q(answer2__icontains=k) | 
                    # Q(reference__icontains=k)
                    Q(non_html__icontains=k)
                ).order_by('-updated_at')#

        context['faqs'] = queryset

    #振り先一覧pdfのパス
    context['furisaki'] = Attachments.objects.filter(file_path__contains="振り先一覧").first()

    #窓口
    queryset = Contacts.objects.all()
    keyword = request.GET.get('all_search')
    if keyword:
        keyword = keyword.split()
        for k in keyword:
            queryset = queryset.filter(
                    Q(name__icontains=k) | 
                    Q(title__icontains=k) | 
                    Q(job__icontains=k) | 
                    Q(tel__icontains=k) | 
                    # Q(searchwords__icontains=k)
                    Q(for_search__icontains=k)
                ).order_by('id')#

        context['contacts'] = queryset


    #自分のノート検索
    keyword = request.GET.get('all_search')
    if keyword:
        keyword = keyword.split()
        for k in keyword:
            queryset = Note.objects.all().filter(
                    Q(owner=request.user) & #自分のものだけ
                    # (Q(title__icontains=k) | Q(body__icontains=k))
                    (Q(title__icontains=k) | Q(non_html__icontains=k) | Q(for_search__icontains=k))
                ).order_by('-updated_at')#

        context['note_set'] = queryset
        note_cnt = queryset.count()

    #シェアのノートも検索
    keyword = request.GET.get('all_search')
    if keyword:
        keyword = keyword.split()
        for k in keyword:
            queryset = Note.objects.all().filter(
                    Q(share__in=[request.user]) & #シェアのものだけ
                    # (Q(title__icontains=k) | Q(body__icontains=k))
                    (Q(title__icontains=k) | Q(non_html__icontains=k) | Q(for_search__icontains=k))
                ).order_by('-updated_at')#

        context['note_set_share'] = queryset
        note_cnt = note_cnt + queryset.count()

    #ノート件数（自分＋シェア）
    context['note_cnt'] = note_cnt


    return render(request, 'myinfo/search_result.html', context)



class ContactsJsonView(BaseDatatableView):
    # モデルの指定
    model = Contacts
    # 表示するフィールドの指定
    # columns = ['id', 'incoming', 'name', 'tel', 'hours', 'title', 'job', 'searchwords', 'attachments']
    columns = ['id', 'incoming', 'name', 'tel', 'hours', 'title', 'job', 'for_search', 'attachments']

    # ↓FKey(M2Mの中間テーブル)でやってみる
    def render_column(self, row, column):
        if column == 'attachments':
            # ↓中間テーブル自作
            # if ContactAttachRel.objects.filter(contact=row.id).exists():
            #     url = ContactAttachRel.objects.filter(contact=row.id).first().attachment.file_path.url
            #     file_name = str(ContactAttachRel.objects.filter(contact=row.id).first().attachment)
            #     iframe ="<iframe src='" + url + "' height=1000 width=100%></iframe>"
            #     #↑と↓で"と'を入れ替えているとOK
            #     return '<a class="btn btn-light btn-icon-split btn-sm mt-1" data-toggle="modal" data-target="#exampleModal" data-sample="' + iframe + '">\
            #             <span class="icon text-gray-600"><i class="fas fa-paperclip"></i></span><span class="text">'+ file_name +'</span></a>'
            
            # ↓中間テーブル自作なし
            attachs = Contacts.objects.get(id=row.id).attachments.all()
            block =""
            if attachs.exists():
                for attach in attachs:
                    # url =attach.first().file_path.url
                    # file_name = str(attach.first())
                    url =attach.file_path.url
                    file_name = str(attach)
                    # iframe ="<iframe src='" + url + "' height=600 width=100%></iframe>"
                    iframe ="<div class='modal-header py-1'>\
                                <button type='button' class='close' data-dismiss='modal' aria-label='Close'>\
                                    <span aria-hidden='true'>&times;</span>\
                                </button>\
                            </div><iframe src='" + url + "' height=1000 width=100%></iframe>"
                    #↑と↓で"と'を入れ替えているとOK
                    block = block + '<a class="btn btn-light btn-icon-split btn-sm mt-1" data-toggle="modal" data-target="#exampleModal" data-sample="' + iframe + '">\
                            <span class="icon text-gray-600"><i class="fas fa-paperclip"></i></span><span class="text">'+ file_name +'</span></a>'+"　"
                
                return block
            # else:
            #     return "なし"
        else:
            return super(ContactsJsonView, self).render_column(row, column)


    # # 検索方法の指定：部分一致
    # def get_filter_method(self):
    #     return super().FILTER_ICONTAINS


    def filter_queryset(self, qs):

        search = self.request.GET.get('search[value]', None)
        if search:
            search_parts = search.split()
            for part in search_parts:
                qs = qs.filter(
                        Q(incoming__icontains=part) | 
                        Q(name__icontains=part) | 
                        Q(title__icontains=part) | 
                        Q(job__icontains=part) | 
                        Q(tel__icontains=part) | 
                        Q(hours__icontains=part) | 
                        # Q(searchwords__icontains=part)
                        Q(for_search__icontains=part)
                    )
        return qs


class DealersJsonView(BaseDatatableView):
    # モデルの指定
    model = Dealers
    # 表示するフィールドの指定
    columns = ['id', 'code5', 'code4', 'name', 'full_name', 'domain', 'customer_desk',	'emergency', 'bc', 'nfs', 'in_house', 'base', 'base_tel']

    # 検索方法の指定：ワード1つならこれだけでOK
    def get_filter_method(self):
        return super().FILTER_ICONTAINS


class ShopsJsonView(BaseDatatableView):
    model = Shops
    # columns = ['id', 'dealer', 'name', 'shopcode', 'tel', 'fax', 'homepage', 'memo', 'kana']
    # ↓でソートはOKでも、検索でエラー
    columns = [
        'id',
        'dealer__name',
        'name',
        'shopcode',
        'tel',
        'fax',
        'homepage',
        'memo',
        'kana',
        'dealer__pk',
        'dealer__code5',
        'dealer__code4',
        'dealer__full_name',
        'dealer__domain',
        'dealer__customer_desk',
        'dealer__emergency',
        'dealer__bc',
        'dealer__nfs',
        'dealer__in_house',
        'dealer__base',
        'dealer__base_tel',
        ]
    def render_column(self, row, column):
        if column == 'dealer__name':
            return row.dealer.name
            # return row.dealer.pk #pkも返せる
        elif column == 'dealer__pk':
            return row.dealer.pk
        elif column == 'dealer__code5':
            return row.dealer.code5
        elif column == 'dealer__code4':
            return row.dealer.code4
        elif column == 'dealer__full_name':
            return row.dealer.full_name
        elif column == 'dealer__domain':
            return row.dealer.domain
        elif column == 'dealer__customer_desk':
            return row.dealer.customer_desk
        elif column == 'dealer__emergency':
            return row.dealer.emergency
        elif column == 'dealer__bc':
            return row.dealer.bc
        elif column == 'dealer__nfs':
            return row.dealer.nfs
        elif column == 'dealer__in_house':
            return row.dealer.in_house
        elif column == 'dealer__base':
            return row.dealer.base
        elif column == 'dealer__base_tel':
            return row.dealer.base_tel
        else:
            return super(ShopsJsonView, self).render_column(row, column)

    # https://pypi.org/project/django-datatables-view/1.20.0/
    # 動作OK
    # def render_column(self, row, column):
    #     if column == 'custom':
    #         return f'{row.dealer}'
    #     else:
    #         return super(ShopsJsonView, self).render_column(row, column)

    # 複数ワード
    def filter_queryset(self, qs):

        search = self.request.GET.get('search[value]', None)
        if search:
            search_parts = search.split()
            for part in search_parts:
                #外部キー検索できる？
                # query = reduce(operator.and_, [ Q(dealer__name__icontains=part) for part in qs ] )
                # qs = qs.filter( query )

                qs = qs.filter(
                        # Q(dealer__icontains=part) | #これがあるとエラーになる
                        Q(dealer__name__icontains=part) | #これでOK
                        Q(name__icontains=part) | 
                        Q(shopcode__icontains=part) | 
                        Q(tel__icontains=part) | 
                        Q(fax__icontains=part) | 
                        Q(homepage__icontains=part) | 
                        Q(memo__icontains=part) | 
                        Q(kana__icontains=part)
                    )
        return qs

# django-ajax-datatable中止
# def contacts(request):
#     return render(request, 'myinfo/contacts_list.html', {})


#ノートlist
def note_list(request):

    notesearchForm = NoteSearchForm(request.GET)

    context = {
        'notesearchForm': notesearchForm,
    }

    if notesearchForm.is_valid():
        #自分の検索
        keyword = notesearchForm.cleaned_data['keyword']
        keyword2 = notesearchForm.cleaned_data['keyword']
        if keyword:
            keyword = keyword.split()
            for k in keyword:
                queryset = Note.objects.all().filter(
                        Q(owner=request.user) & #自分のものだけ
                        # (Q(title__icontains=k) | Q(body__icontains=k))
                        (Q(title__icontains=k) | Q(non_html__icontains=k) | Q(for_search__icontains=k))
                    ).order_by('-updated_at')#

            context['note_set'] = queryset
            context['selected_tab'] = '検索結果'

        #シェアも検索
        if keyword2:
            keyword2 = keyword2.split()
            for k in keyword2:
                queryset = Note.objects.all().filter(
                        Q(share__in=[request.user]) & #シェアのものだけ
                        # (Q(title__icontains=k) | Q(body__icontains=k))
                        (Q(title__icontains=k) | Q(non_html__icontains=k) | Q(for_search__icontains=k))
                    ).order_by('-updated_at')#

            context['note_set_share'] = queryset


    else:
        notesearchForm = NoteSearchForm()
        # note_set = Note.objects.all().order_by('-updated_at')
        note_set = Note.objects.filter(owner=request.user).order_by('-updated_at')#自分のものだけ
        page_obj = paginate_queryset(request, note_set, 20)#ページネーション用
        context['page_obj'] = page_obj
        context['note_set'] = page_obj.object_list
        context['selected_tab'] = '自分'

    return render(request, 'myinfo/note_list.html', context)

#ノート、シェア用タブ
def note_tab(request, p):

    notesearchForm = NoteSearchForm(request.GET)

    context = {
        'notesearchForm': notesearchForm,
    }

    # 一度queryset = Faqs.objects.all()と刻む必要はない
    queryset = Note.objects.filter(
                Q(share__in=[request.user])
            ).order_by('-updated_at')
    context['selected_tab'] = p
    context['note_set'] = queryset

    return render(request, 'myinfo/note_list.html', context)


#ノート新規
def note_create(request):
    if request.method == "POST":
        form = NoteCreateForm(request.POST, request.FILES)

        if form.is_valid(): 
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.updated_at = timezone.datetime.now()

            #html除去
            obj.non_html = strip_tags(request.POST.get('body'))

            obj.save()
            form.save_m2m() #formのメソッド、M2Mフィードで必要

            #ブラウザ通知
            # data = {
            #     'app_id': '6027ee57-82ec-485b-a5a5-6c976de75cb1',
            #     'included_segments': ['All'],
            #     'contents': {'en': 'note create'},
            #     'headings': {'en': 'Noteが作成されました'},
            #     'url': resolve_url('myinfo:note_list'),
            # }
            # requests.post(
            #     "https://onesignal.com/api/v1/notifications",
            #     headers={'Authorization': 'Basic NDQ4Y2RiZTctNTgxMy00ZTc2LWFiYzctZTRiZGMyMGYwNjJh'},  # 先頭にBasic という文字列がつく
            #     json=data,
            # )   

            return redirect('myinfo:note_list')

    else:
        form = NoteCreateForm

    return render(request, 'myinfo/note_create.html', {'form': form })


#ノート削除
def note_delete(request, pk):
    Note.objects.filter(pk=pk).delete()
    messages.info(request, '削除しました！')
    return redirect(request.META['HTTP_REFERER'])#元のページに戻る


#Update関数ビューつくる
def note_update(request, pk, *args, **kwargs):

    note = get_object_or_404(Note, pk=pk)

    #外部キーなので_set.all()でなくrelated_nameで
    share = note.share.all()
    
    if request.method == 'POST':
        form = NoteCreateForm(request.POST, request.FILES, instance=note)

        if form.is_valid(): 
            obj = form.save(commit=False)
            obj.owner = request.user

            #html除去
            obj.non_html = strip_tags(request.POST.get('body'))

            obj.save()
            form.save_m2m() #formのメソッド、M2Mフィードで必要

            messages.success(request, '更新しました！')
            return redirect('myinfo:note_list')

        else:
            messages.error(request, '更新できませんでした。内容を確認してください。')
            return redirect('myinfo:note_update', pk=pk)


    # 一覧表示からの遷移や、確認画面から戻った時
    form =  NoteCreateForm(instance=note)

    context ={
        'form': form,
        'note':note,        
    }

    return render(request, 'myinfo/note_create.html', context)