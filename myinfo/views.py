from django.shortcuts import render, redirect, get_object_or_404, redirect
from django.http import HttpResponse, Http404

from django.views import generic
# from .models import Information, InfoCategory, Attachments, Notifications, ReadStates, InfoComments
from .models import *
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .forms import InformationForm, InformationEditForm, SearchForm, FaqSearchForm

from django.contrib import messages

# from django.contrib.auth.models import User
# from django.contrib.auth import get_user_model
from accounts.models import User

from django.utils import timezone
import os

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from django_datatables_view.base_datatable_view import BaseDatatableView


#関数ビューで通知の中間テーブルCreateを作ってみる
def add_fbvform(request):
    if request.method == "POST":
        form = InformationForm(request.POST, request.FILES)

        if form.is_valid(): 
            obj = form.save(commit=False)
            obj.user = request.user
            obj.created_at = timezone.datetime.now()
            obj.updated_at = timezone.datetime.now()
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
            # user = User.objects.get(pk=request.POST["notification_user"])
            # Notifications.objects.create(user=user, information=obj)

            #通知：選択したユーザー
            result = request.POST.getlist("tags")
            for user in result:
                # user_instance = User.objects.get(pk=user)#これ出来ない・
                user_instance = get_object_or_404(User, pk=user)
                # Notifications.objects.create(user=user_instance, information=obj)
                #既読も同じでok？
                ReadStates.objects.create(user=user_instance, information=obj)

            #↓これ↓が最終
            # file = request.FILES.get('file')
            # Attachments.objects.create(file_path=file, information=obj)
            #↓これ↑が最終

                # for file in files:
                #     Attachments.objects.create(file_path=file, information=obj)

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
                        Q(body__icontains=k)
                    ).order_by('-updated_at')#

            context['informations'] = queryset
    else:
        searchForm = SearchForm()
        informations = Information.objects.all().order_by('-updated_at')
        page_obj = paginate_queryset(request, informations, 20)#ページネーション用
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

    if faqsearchForm.is_valid():
        queryset = Faqs.objects.all()
        keyword = faqsearchForm.cleaned_data['keyword']
        if keyword:
            keyword = keyword.split()
            for k in keyword:
                queryset = queryset.filter(
                        Q(question__icontains=k) | 
                        Q(answer1__icontains=k) | 
                        Q(answer2__icontains=k) | 
                        Q(reference__icontains=k)
                    ).order_by('-updated_at')#

            context['faqs'] = queryset
    else:
        faqsearchForm = FaqSearchForm()
        faqs = Faqs.objects.all().order_by('-updated_at', 'id')
        page_obj = paginate_queryset(request, faqs, 50)#ページネーション用
        context['page_obj'] = page_obj
        context['faqs'] = page_obj.object_list


    return render(request, 'myinfo/faqs.html', context)


#FAQ Datatablesバージョン
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